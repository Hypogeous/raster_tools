from collections.abc import Iterable, Iterator, Sequence
from functools import partial

import dask
import dask.array as da
import dask.dataframe as dd
import numba as nb
import numpy as np
import pandas as pd
from dask_image import ndmeasure

from raster_tools._types import F64, I64
from raster_tools._utils import is_int, is_str
from raster_tools.raster import Raster, RasterNoDataError, get_raster
from raster_tools.vector import Vector, get_vector

__all__ = ["ZONAL_STAT_FUNCS", "zonal_stats"]


def _handle_empty(func):
    def wrapped(x, axis=None, keepdims=False):
        if x.size > 0 or np.isnan(x.size):
            try:
                return func(x, axis=axis, keepdims=keepdims)
            except ValueError:
                pass
        return np.array([], dtype=x.dtype)

    return wrapped


# np.nan{min, max} both throw errors for empty chumks. dask.array.nan{min, max}
# handles empty chunks but requires that the chunk sizes be known at runtime.
# This safely handles empty chunks. There may still be corner cases that have
# not been found but for now it works.
_nanmin_empty_safe = _handle_empty(np.nanmin)
_nanmax_empty_safe = _handle_empty(np.nanmax)


def _nan_min(x):
    return da.reduction(
        x,
        _nanmin_empty_safe,
        _nanmin_empty_safe,
        axis=None,
        keepdims=False,
        dtype=x.dtype,
    )


def _nan_max(x):
    return da.reduction(
        x,
        _nanmax_empty_safe,
        _nanmax_empty_safe,
        axis=None,
        keepdims=False,
        dtype=x.dtype,
    )


def _nan_count(x):
    return da.count_nonzero(~np.isnan(x))


def _nan_median(x):
    x = da.asarray(x)
    return da.nanmedian(x, axis=0)


def _nan_unique(x):
    return _nan_count(da.unique(x))


def _flatten_gen(x):
    """
    A generator that recursively yields numpy arrays from arbitrarily nested
    lists of arrays.
    """
    for xi in x:
        if isinstance(x, Iterable) and not isinstance(xi, np.ndarray):
            yield from _flatten_gen(xi)
        else:
            yield xi


def _flatten(x):
    """Flatten nested lists of arrays."""
    if isinstance(x, np.ndarray):
        return [x]
    return list(_flatten_gen(x))


def _recursive_map(func, *seqs):
    """Apply a function to items in nested sequences."""
    if isinstance(seqs[0], (list, Iterator)):
        return [_recursive_map(func, *items) for items in zip(*seqs)]
    return func(*seqs)


def _unique_with_counts_chunk(x, computing_meta=False, axis=(), **kwargs):
    """Reduce a dask chunk to a dict of unique values and counts.

    This is the leaf operation in the reduction tree.
    """
    if computing_meta:
        return x
    x_non_nan = x[~np.isnan(x)]
    values, counts = np.unique(x_non_nan, return_counts=True)
    while values.ndim < len(axis):
        values = np.expand_dims(values, axis=0)
        counts = np.expand_dims(counts, axis=0)
    return {"values": values, "counts": counts}


def _ravel_key(item, key):
    return item[key].ravel()


_ravel_values = partial(_ravel_key, key="values")
_ravel_counts = partial(_ravel_key, key="counts")


def _split_concat(pairs, split_func):
    # Split out a key from lists of dicts, ravel them, and concat all together
    split = _recursive_map(split_func, pairs)
    return np.concatenate(_flatten(split))


def _unique_with_counts_combine(
    pairs, computing_meta=False, axis=(), **kwargs
):
    """Merge/combine branches of the unique-with-counts reduction tree.

    This includes results from multiple _unique_with_counts_chunk calls and
    from prior _unique_with_counts_combine calls.
    """
    values = (
        _recursive_map(_ravel_values, pairs) if not computing_meta else pairs
    )
    values = np.concatenate(_flatten(values))
    if computing_meta:
        return np.array([[[0]]], dtype=pairs.dtype)

    counts = _split_concat(pairs, _ravel_counts)
    res = {v: 0 for v in values}
    for v, c in zip(values, counts):
        res[v] += c
    values = np.array(list(res.keys()))
    counts = np.array(list(res.values()))
    while values.ndim < len(axis):
        values = np.expand_dims(values, axis=0)
        counts = np.expand_dims(counts, axis=0)
    return {"values": values, "counts": counts}


def _mode_agg(pairs, computing_meta=False, axis=(), **kwargs):
    """Perform the final aggregation to a single mode value."""
    values = (
        _split_concat(pairs, _ravel_values) if not computing_meta else pairs
    )
    if computing_meta:
        return pairs.dtype.type(0)
    if len(values) == 0:
        # See note below about wrapping in np.array()
        return np.array(np.nan)
    counts = _split_concat(pairs, _ravel_counts)
    res = {v: 0 for v in values}
    for v, c in zip(values, counts):
        res[v] += c
    values = res.keys()
    counts = res.values()
    sorted_pairs = sorted(zip(counts, values), reverse=True)
    # Find the minimum mode when there is a tie. This is the same behavior as
    # scipy.
    i = -1
    c = sorted_pairs[0][0]
    for pair in sorted_pairs:
        if pair[0] == c:
            i += 1
        else:
            break
    # NOTE: wrapping the value in an array is a hack to prevent dask from
    # mishandling the return value as an array with dims, leading to index
    # errors. I can't pierce the veil of black magic that is causing the
    # mishandling so this is the best fix I can come up with.
    return np.array(sorted_pairs[i][1])


def _nan_mode(x):
    """
    Compute the statistical mode of an array using a dask reduction operation.
    """
    return da.reduction(
        x,
        chunk=_unique_with_counts_chunk,
        combine=_unique_with_counts_combine,
        aggregate=_mode_agg,
        # F64 to allow for potential empty input array. In that case a NaN is
        # returned.
        dtype=F64,
        # Turn off concatenation to prevent dask from trying to concat the
        # dicts of variable length values and counts. Dask tries to concat
        # along the wrong axis, which causes errors.
        concatenate=False,
    )


@nb.jit(nopython=True, nogil=True)
def _entropy(values, counts):
    if len(values) == 0:
        return np.nan
    res = {v: 0 for v in values}
    for v, c in zip(values, counts):
        res[v] += c
    counts = res.values()
    entropy = 0.0
    frac = 1 / len(res)
    for cnt in counts:
        p = cnt * frac
        entropy -= p * np.log(p)
    return entropy


@nb.jit(nopython=True, nogil=True)
def _asm(values, counts):
    if len(values) == 0:
        return np.nan
    res = {v: 0 for v in values}
    for v, c in zip(values, counts):
        res[v] += c
    counts = res.values()
    asm = 0.0
    frac = 1 / len(res)
    for cnt in counts:
        p = cnt * frac
        asm += p * p
    return asm


def _entropy_asm_agg(
    pairs, compute_entropy, computing_meta=False, axis=(), **kwargs
):
    """Perform the final aggregation to a single entropy or ASM value."""
    if computing_meta:
        return 0
    values = _split_concat(pairs, _ravel_values)
    if len(values) == 0:
        return np.array([])
    counts = _split_concat(pairs, _ravel_counts)
    # NOTE: wrapping the value in an array is a hack to prevent dask from
    # mishandling the return value as an array with dims, leading to index
    # errors. I can't pierce the veil of black magic that is causing the
    # mishandling so this is the best fix I can come up with.
    if compute_entropy:
        return np.array(_entropy(values, counts))
    return np.array(_asm(values, counts))


def _nan_entropy(x):
    """Compute the entropy of an array using a dask reduction operation."""
    return da.reduction(
        x,
        # mode chunk and combine funcs can be reused here
        chunk=_unique_with_counts_chunk,
        combine=_unique_with_counts_combine,
        aggregate=partial(_entropy_asm_agg, compute_entropy=True),
        dtype=F64,
        # Turn off concatenation to prevent dask from trying to concat the
        # dicts of variable length values and counts. Dask tries to concat
        # along the wrong axis, which causes errors.
        concatenate=False,
    )


def _nan_asm(x):
    """Compute the ASM of an array using a dask reduction operation.

    Angular second moment.
    """
    return da.reduction(
        x,
        # mode chunk and combine funcs can be reused here
        chunk=_unique_with_counts_chunk,
        combine=_unique_with_counts_combine,
        aggregate=partial(_entropy_asm_agg, compute_entropy=False),
        dtype=F64,
        # Turn off concatenation to prevent dask from trying to concat the
        # dicts of variable length values and counts. Dask tries to concat
        # along the wrong axis, which causes errors.
        concatenate=False,
    )


_ZONAL_STAT_FUNCS = {
    "asm": _nan_asm,
    "count": _nan_count,
    "entropy": _nan_entropy,
    "max": _nan_max,
    "mean": da.nanmean,
    "median": _nan_median,
    "min": _nan_min,
    "mode": _nan_mode,
    "std": da.nanstd,
    "sum": da.nansum,
    "unique": _nan_unique,
    "var": da.nanvar,
}
# The set of valid zonal function names/keys
ZONAL_STAT_FUNCS = frozenset(_ZONAL_STAT_FUNCS)


def _get_zonal_data(vec, raster, all_touched=True):
    if raster.shape[0] > 1:
        raise ValueError("Only single band rasters are allowed")
    try:
        raster_clipped = raster.clip_box(
            # Use persist here to kick off computation of the bounds in the
            # background. The bounds have to be computed one way or another at
            # this point and persist allows it to start before the block occurs
            # in clip_box. If a large number of zonal calculations are being
            # carried out, this can provide a significant times savings.
            *dask.persist(vec.to_crs(raster.crs.wkt).bounds)[0]
        )
    except RasterNoDataError:
        return da.from_array([], dtype=raster_clipped.dtype)
    vec_mask = vec.to_raster(raster_clipped, all_touched=all_touched) > 0
    values = raster_clipped._rs.data[vec_mask._rs.data]
    # Filter null values
    if raster._masked:
        nv_mask = raster_clipped._mask[vec_mask._rs.data]
        values = values[~nv_mask]
    # Output is a 1-D dask array with unknown size
    return values


def _build_zonal_stats_data(data_raster, feat_raster, feat_labels, stats):
    nbands = data_raster.shape[0]
    feat_data = feat_raster._rs.data
    # data will end up looking like:
    # {
    #   # band number
    #   1: {
    #     # Stat results
    #     "mean": [X, X, X], <- dask array
    #     "std": [X, X, X],
    #     ...
    #   },
    #   2: {
    #     # Stat results
    #     "mean": [X, X, X],
    #     "std": [X, X, X],
    #     ...
    #   },
    #   ...
    data = {}
    for ibnd in range(nbands):
        ibnd += 1
        data[ibnd] = {}
        rs_data = get_raster(
            data_raster.get_bands(ibnd), null_to_nan=True
        )._rs.data
        for f in stats:
            result_delayed = dask.delayed(ndmeasure.labeled_comprehension)(
                rs_data,
                feat_data,
                feat_labels,
                _ZONAL_STAT_FUNCS[f],
                F64,
                np.nan,
            )
            data[ibnd][f] = da.from_delayed(
                result_delayed,
                feat_labels.shape,
                dtype=F64,
                meta=np.array([], dtype=F64),
            )
    return data


def _create_dask_range_index(start, stop):
    # dask.dataframe only allows dask.dataframe.index objects but doesn't have
    # a way to create them. this is a hack to create one using from_pandas.
    dummy = pd.DataFrame(
        {"tmp": np.zeros(stop - start, dtype="u1")},
        index=pd.RangeIndex(start, stop),
    )
    return dd.from_pandas(dummy, 1).index


def _build_zonal_stats_dataframe(zonal_data):
    bands = list(zonal_data)
    snames = list(zonal_data[bands[0]])
    n = zonal_data[bands[0]][snames[0]].size
    # Get the number of partitions that dask thinks is reasonable. The data
    # arrays have chunks of size 1 so we need to rechunk later and then
    # repartition everything else in the dataframe to match.
    nparts = zonal_data[bands[0]][snames[0]].rechunk().npartitions

    df = None
    for bnd in bands:
        df_part = None
        band_data = zonal_data[bnd]
        band = da.full(n, bnd, dtype=I64)
        # We need to create an index because the concat operation later will
        # blindly paste in each dataframe's index. If an explicit index is not
        # set, the default is a range index from 0 to n. Thus the final
        # resulting dataframe would have identical indexes chained end-to-end:
        # [0, 1, ..., n-1, 0, 1, ..., n-1, 0, 1..., n-1]. By setting an index
        # we get [0, 1, ..., n, n+1, ..., n + n, ...].
        ind_start = n * (bnd - 1)
        ind_end = ind_start + n
        index = _create_dask_range_index(ind_start, ind_end)
        df_part = band.to_dask_dataframe("band", index=index).to_frame()
        # Repartition to match the data
        df_part = df_part.repartition(npartitions=nparts)
        index = index.repartition(npartitions=nparts)
        for name in snames:
            df_part[name] = (
                band_data[name].rechunk().to_dask_dataframe(name, index=index)
            )
        if df is None:
            df = df_part
        else:
            # Use interleave_partitions to keep partition and division info
            df = dd.concat([df, df_part], interleave_partitions=True)
    return df


def zonal_stats(features, data_raster, stats, raster_feature_values=None):
    """Apply stat functions to a raster based on a set of features.

    Parameters
    ----------
    features : str, Vector, Raster
        A `Vector` or path string pointing to a vector file or a categorical
        Raster. The vector features are used like cookie cutters to pull data
        from the `data_raster` bands. If `features` is a Raster, it must be an
        int dtype and have only one band.
    data_raster : Raster, str
        A `Raster` or path string pointing to a raster file. The data raster
        to pull data from and apply the stat functions to.
    stats : str, list of str
        A single string or list of strings corresponding to stat funcstions.
        These functions will be applied to the raster data for each of the
        features in `features`. Valid string values:

        'asm'
            Angular second moment. Applies -sum(P(g)**2) where P(g) gives the
            probability of g within the neighborhood.
        'count'
            Count valid cells.
        'entropy'
            Calculates the entropy. Applies -sum(P(g) * log(P(g))). See 'asm'
            above.
        'max'
            Find the maximum value.
        'mean'
            Calculate the mean.
        'median'
            Calculate the median value.
        'min'
            Find the minimum value.
        'mode'
            Compute the statistical mode of the data. In the case of a tie, the
            lowest value is returned.
        'std'
            Calculate the standard deviation.
        'sum'
            Calculate the sum.
        'unique'
            Count unique values.
        'var'
            Calculate the variance.
    raster_feature_values : sequence of ints, optional
        Unique values to be used when the `features` argument is a Raster. If
        `features` is a Raster and this is not provided the unique values in
        the raster will be calculated.

    Returns
    -------
    dask.dataframe.DataFrame
        A delayed dask DataFrame. The columns are the values in `stats` plus a
        column indicating the band the calculation was carried out on. Each row
        is the set of statistical calculations carried out on data pulled from
        `data_raster` based on the corresponding feature in `features`. NaN
        values indicate where a feature was outside of the raster or all data
        under the feature was null.

    """
    if is_str(features) or isinstance(features, Vector):
        features = get_vector(features)
    elif isinstance(features, Raster):
        if not is_int(features.dtype):
            raise TypeError("Feature raster must be an integer type.")
        if features.shape[0] > 1:
            raise ValueError("Feature raster must have only 1 band.")
    else:
        raise TypeError(
            "Could not understand features arg. Must be Vector, str or Raster"
        )
    data_raster = get_raster(data_raster)
    if is_str(stats):
        stats = [stats]
    elif isinstance(stats, Sequence):
        stats = list(stats)
        if not stats:
            raise ValueError("No stat functions provide")
    else:
        raise ValueError(f"Could not understand stats arg: {repr(stats)}")
    for stat in stats:
        if stat not in ZONAL_STAT_FUNCS:
            raise ValueError(f"Invalid stats function: {repr(stat)}")
    if isinstance(features, Raster):
        if features.crs != data_raster.crs:
            raise ValueError("Feature raster CRS must match data raster")
        if features.shape != data_raster.shape:
            raise ValueError("Feature raster shape must match data raster")

    feature_labels = None
    features_raster = None
    if isinstance(features, Vector):
        feature_labels = np.arange(1, len(features) + 1)
        features_raster = features.to_raster(data_raster)
    else:
        if raster_feature_values is None:
            (raster_feature_values,) = dask.compute(
                np.unique(features._rs.data)
            )
        else:
            raster_feature_values = np.atleast_1d(raster_feature_values)
            raster_feature_values = raster_feature_values[
                raster_feature_values > 0
            ]
        feature_labels = raster_feature_values
        features_raster = features

    data = _build_zonal_stats_data(
        data_raster, features_raster, feature_labels, stats
    )
    df = _build_zonal_stats_dataframe(data)
    return df
