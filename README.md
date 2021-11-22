# raster_tools
RMRS Raster Utility Project

## Dependencies
* [cython](https://cython.readthedocs.io/en/latest/)
* [dask](https://dask.org/)
* [dask_image](https://image.dask.org/en/latest/)
* [dask-geopandas](https://github.com/geopandas/dask-geopandas)
* [geopandas](https://geopandas.org/en/stable/)
* [numba](https://numba.pydata.org/)
* [rasterio](https://rasterio.readthedocs.io/en/latest/)
* [rioxarray](https://corteva.github.io/rioxarray/stable/)
* [xarray](https://xarray.pydata.org/en/stable/)
* [cupy](https://cupy.dev/): optional and very experimental

## Before Using
Some of this package's modules use
[cython](https://cython.readthedocs.io/en/latest/) code.  You must compile the
Cython code in order to use this package. To do this, make sure that the cython
package is installed in your environment and run the following in the project
root:
```sh
python setup.py build_ext --inplace
```
This will compile the necessary shared objects that python can use.
