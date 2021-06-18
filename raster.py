import operator
import os
import xarray as xr
from numbers import Number


def _validate_file(path):
    if os.path.isfile(path):
        return path
    raise FileNotFoundError(f"Could not find file: '{path}'")


def _is_str(value):
    return isinstance(value, str)


def _is_scalar(value):
    return isinstance(value, Number)


def _is_raster_class(value):
    return isinstance(value, Raster)


TIFF_EXTS = frozenset((".tif", ".tiff"))
BATCH_EXTS = frozenset((".bch",))
NC_EXTS = frozenset((".nc",))


def _parse_path(path):
    _validate_file(path)
    ext = os.path.splitext(path)[-1].lower()
    if not ext:
        raise ValueError("Could not determine file type")
    if ext in TIFF_EXTS:
        # TODO: chunking logic
        return xr.open_rasterio(path)
    elif ext in BATCH_EXTS:
        raise NotImplementedError()
    else:
        raise ValueError("Unknown file type")


def _parse_input(rs_in):
    if _is_str(rs_in):
        return _parse_path(rs_in)
    elif isinstance(rs_in, Raster):
        return rs_in
    elif isinstance(rs_in, (xr.DataArray, xr.Dataset)):
        return rs_in


_ARITHMETIC_OPS = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
}


class Raster:
    def __init__(self, raster):
        rs = _parse_input(raster)
        if _is_raster_class(rs):
            self._rs = rs._rs
        else:
            self._rs = rs
        self.shape = self._rs.shape

    def close(self):
        self._rs.close()

    def save(self, path):
        ext = os.path.splitext(path)[-1].lower()
        if ext in TIFF_EXTS:
            # TODO: handle saving to tiff
            NotImplementedError()
        elif ext in NC_EXTS:
            self._rs.to_netcdf(path)
        else:
            raise NotImplementedError()

    def eval(self):
        self._rs.compute()

    def arithmetic(self, raster_or_scalar, op):
        # TODO: handle mapping of list of values to bands
        if op not in _ARITHMETIC_OPS:
            raise ValueError(f"Unknown arithmetic operation: '{op}'")
        # TODO:Fix this ugly block
        if _is_scalar(raster_or_scalar):
            operand = raster_or_scalar
        elif _is_raster_class(raster_or_scalar):
            operand = raster_or_scalar._rs
        else:
            operand = _parse_input(raster_or_scalar)
        return Raster(_ARITHMETIC_OPS[op](self._rs, operand))

    def add(self, raster_or_scalar):
        return self.arithmetic(raster_or_scalar, "+")

    def __add__(self, other):
        return self.add(other)

    def __radd__(self, other):
        return self.add(other)

    def subtract(self, raster_or_scalar):
        return self.arithmetic(raster_or_scalar, "-")

    def __sub__(self, other):
        return self.subtract(other)

    def __rsub__(self, other):
        return self.negate().add(other)

    def multiply(self, raster_or_scalar):
        return self.arithmetic(raster_or_scalar, "*")

    def __mul__(self, other):
        return self.multiply(other)

    def __rmul__(self, other):
        return self.multiply(other)

    def divide(self, raster_or_scalar):
        return self.arithmetic(raster_or_scalar, "/")

    def __truediv__(self, other):
        return self.divide(other)

    def __rtruediv__(self, other):
        return self.pow(-1).multiply(other)

    def pow(self, value):
        return Raster(self._rs ** value)

    def __pow__(self, value):
        return self.pow(value)

    def __pos__(self):
        return self

    def negate(self):
        return Raster(-self._rs)

    def __neg__(self):
        return self.negate()

    def convolve2d(self, kernel, fill_value=0):
        # TODO: validate kernel
        # TODO: handle attr propagation
        nr, nc = kernel.shape
        kernel = xr.DataArray(kernel, dims=("kx", "ky"))
        min_periods = (nr // 2 + 1) * (nc // 2 + 1)
        rs_out = (
            self._rs.rolling(x=nr, y=nc, min_periods=min_periods, center=True)
            .construct(x="kx", y="ky", fill_value=fill_value)
            .dot(kernel)
        )
        return Raster(rs_out)


def test():
    # Quick function to see if any errors get thrown
    r1 = Raster(
        "../datasets/DC_Example/data/NoMGT_2022/Total3Run_DF_10_NoMGT_2022_V20210420.tif"
    )
    r2 = Raster(
        "../datasets/DC_Example/data/NoMGT_2022/Total3Run_DF_15_NoMGT_2022_V20210420.tif"
    )
    r3 = (
        r1.add(r2)
        .multiply(r1)
        .multiply(3)
        .multiply(0.3)
        .subtract(r2)
        .divide(2)
        .eval()
    )


test()
