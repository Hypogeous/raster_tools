import dask
import numpy as np
import unittest

from raster_tools import Raster
from raster_tools.raster import (
    _BINARY_ARITHMETIC_OPS,
    _DTYPE_INPUT_TO_DTYPE,
    U8,
    U16,
    U32,
    U64,
    I8,
    I16,
    I32,
    I64,
    F16,
    F32,
    F64,
    F128,
    BOOL,
)


def rs_eq_array(rs, ar):
    return (rs._rs.values == ar).all()


class TestRasterMath(unittest.TestCase):
    def setUp(self):
        self.rs1 = Raster("test/data/elevation_small.tif")
        self.rs1_np = self.rs1._rs.values
        self.rs2 = Raster("test/data/elevation2_small.tif")
        self.rs2_np = self.rs2._rs.values

    def tearDown(self):
        self.rs1.close()
        self.rs2.close()

    def test_add(self):
        # Raster + raster
        truth = self.rs1_np + self.rs2_np
        rst = self.rs1.add(self.rs2)
        self.assertTrue(rs_eq_array(rst, truth))
        rst = self.rs2.add(self.rs1)
        self.assertTrue(rs_eq_array(rst, truth))
        rst = self.rs1 + self.rs2
        self.assertTrue(rs_eq_array(rst, truth))
        rst = self.rs2 + self.rs1
        self.assertTrue(rs_eq_array(rst, truth))
        # Raster + scalar
        for v in [-23, 0, 1, 2, 321]:
            truth = self.rs1_np + v
            rst = self.rs1.add(v)
            self.assertTrue(rs_eq_array(rst, truth))
            rst = self.rs1 + v
            self.assertTrue(rs_eq_array(rst, truth))
            rst = v + self.rs1
            self.assertTrue(rs_eq_array(rst, truth))
        for v in [-23.3, 0.0, 1.0, 2.0, 321.4]:
            truth = self.rs1_np + v
            rst = self.rs1.add(v)
            self.assertTrue(rs_eq_array(rst, truth))
            rst = self.rs1 + v
            self.assertTrue(rs_eq_array(rst, truth))
            rst = v + self.rs1
            self.assertTrue(rs_eq_array(rst, truth))

    def test_subtract(self):
        # Raster - raster
        truth = self.rs1_np - self.rs2_np
        rst = self.rs1.subtract(self.rs2)
        self.assertTrue(rs_eq_array(rst, truth))
        rst = self.rs2.subtract(self.rs1)
        self.assertTrue(rs_eq_array(rst, -truth))
        rst = self.rs1 - self.rs2
        self.assertTrue(rs_eq_array(rst, truth))
        rst = self.rs2 - self.rs1
        self.assertTrue(rs_eq_array(rst, -truth))
        # Raster - scalar
        for v in [-1359, 0, 1, 2, 42]:
            truth = self.rs1_np - v
            rst = self.rs1.subtract(v)
            self.assertTrue(rs_eq_array(rst, truth))
            rst = self.rs1 - v
            self.assertTrue(rs_eq_array(rst, truth))
            rst = v - self.rs1
            self.assertTrue(rs_eq_array(rst, -truth))
        for v in [-1359.2, 0.0, 1.0, 2.0, 42.5]:
            truth = self.rs1_np - v
            rst = self.rs1.subtract(v)
            self.assertTrue(rs_eq_array(rst, truth))
            rst = self.rs1 - v
            self.assertTrue(rs_eq_array(rst, truth))
            rst = v - self.rs1
            self.assertTrue(rs_eq_array(rst, -truth))

    def test_mult(self):
        # Raster * raster
        truth = self.rs1_np * self.rs2_np
        rst = self.rs1.multiply(self.rs2)
        self.assertTrue(rs_eq_array(rst, truth))
        rst = self.rs2.multiply(self.rs1)
        self.assertTrue(rs_eq_array(rst, truth))
        rst = self.rs1 * self.rs2
        self.assertTrue(rs_eq_array(rst, truth))
        rst = self.rs2 * self.rs1
        self.assertTrue(rs_eq_array(rst, truth))
        # Raster * scalar
        for v in [-123, 0, 1, 2, 345]:
            truth = self.rs1_np * v
            rst = self.rs1.multiply(v)
            self.assertTrue(rs_eq_array(rst, truth))
            rst = self.rs1 * v
            self.assertTrue(rs_eq_array(rst, truth))
            rst = v * self.rs1
            self.assertTrue(rs_eq_array(rst, truth))
        for v in [-123.9, 0.0, 1.0, 2.0, 345.3]:
            truth = self.rs1_np * v
            rst = self.rs1.multiply(v)
            self.assertTrue(rs_eq_array(rst, truth))
            rst = self.rs1 * v
            self.assertTrue(rs_eq_array(rst, truth))
            rst = v * self.rs1
            self.assertTrue(rs_eq_array(rst, truth))

    def test_div(self):
        # Raster / raster
        truth = self.rs1_np / self.rs2_np
        rst = self.rs1.divide(self.rs2)
        self.assertTrue(rs_eq_array(rst, truth))
        rst = self.rs2.divide(self.rs1)
        self.assertTrue(rs_eq_array(rst, 1 / truth))
        rst = self.rs1 / self.rs2
        self.assertTrue(rs_eq_array(rst, truth))
        rst = self.rs2 / self.rs1
        self.assertTrue(rs_eq_array(rst, 1 / truth))
        # Raster / scalar, scalar / raster
        for v in [-123, -1, 1, 2, 345]:
            truth = self.rs1_np / v
            rst = self.rs1.divide(v)
            self.assertTrue(rs_eq_array(rst, truth))
            rst = self.rs1 / v
            self.assertTrue(rs_eq_array(rst, truth))
            rst = v / self.rs1
            np.testing.assert_array_almost_equal(rst._rs.values, 1 / truth)
        for v in [-123.8, -1.0, 1.0, 2.0, 345.6]:
            truth = self.rs1_np / v
            rst = self.rs1.divide(v)
            self.assertTrue(rs_eq_array(rst, truth))
            rst = self.rs1 / v
            self.assertTrue(rs_eq_array(rst, truth))
            rst = v / self.rs1
            np.testing.assert_array_almost_equal(rst._rs.values, 1 / truth)

    def test_mod(self):
        # Raster % raster
        truth = self.rs1_np % self.rs2_np
        rst = self.rs1.mod(self.rs2)
        self.assertTrue(rs_eq_array(rst, truth))
        rst = self.rs1 % self.rs2
        self.assertTrue(rs_eq_array(rst, truth))
        truth = self.rs2_np % self.rs1_np
        rst = self.rs2.mod(self.rs1)
        self.assertTrue(rs_eq_array(rst, truth))
        rst = self.rs2 % self.rs1
        self.assertTrue(rs_eq_array(rst, truth))
        # Raster % scalar, scalar % raster
        for v in [-123, -1, 1, 2, 345]:
            truth = self.rs1_np % v
            rst = self.rs1.mod(v)
            self.assertTrue(rs_eq_array(rst, truth))
            rst = self.rs1 % v
            self.assertTrue(rs_eq_array(rst, truth))
            truth = v % self.rs1_np
            rst = v % self.rs1
            self.assertTrue(rs_eq_array(rst, truth))
        for v in [-123.8, -1.0, 1.0, 2.0, 345.6]:
            truth = self.rs1_np % v
            rst = self.rs1.mod(v)
            self.assertTrue(rs_eq_array(rst, truth))
            rst = self.rs1 % v
            self.assertTrue(rs_eq_array(rst, truth))
            truth = v % self.rs1_np
            rst = v % self.rs1
            self.assertTrue(rs_eq_array(rst, truth))

    def test_power(self):
        # Raster ** raster
        rs1 = self.rs1 / self.rs1._rs.max().values.item() * 2
        rs2 = self.rs2 / self.rs2._rs.max().values.item() * 2
        rs1_np = self.rs1_np / self.rs1_np.max() * 2
        rs2_np = self.rs2_np / self.rs2_np.max() * 2
        truth = rs1_np ** rs2_np
        rst = rs1.pow(rs2)
        self.assertTrue(rs_eq_array(rst, truth))
        rst = rs2.pow(rs1)
        self.assertTrue(rs_eq_array(rst, truth))
        rst = rs1 ** rs2
        self.assertTrue(rs_eq_array(rst, truth))
        truth = rs2_np ** rs1_np
        rst = rs2 ** rs1
        self.assertTrue(rs_eq_array(rst, truth))
        # Raster ** scalar, scalar ** raster
        for v in [-10, -1, 1, 2, 11]:
            truth = rs1_np ** v
            rst = rs1.pow(v)
            self.assertTrue(rs_eq_array(rst, truth))
            rst = rs1 ** v
            self.assertTrue(rs_eq_array(rst, truth))
            # Avoid complex numbers issues
            if v >= 0:
                truth = v ** rs1_np
                rst = v ** rs1
                self.assertTrue(rs_eq_array(rst, truth))
        for v in [-10.5, -1.0, 1.0, 2.0, 11.3]:
            truth = rs1_np ** v
            rst = rs1.pow(v)
            self.assertTrue(rs_eq_array(rst, truth))
            rst = rs1 ** v
            self.assertTrue(rs_eq_array(rst, truth))
            # Avoid complex numbers issues
            if v >= 0:
                truth = v ** rs1_np
                rst = v ** rs1
                self.assertTrue(rs_eq_array(rst, truth))


class TestLogicalOps(unittest.TestCase):
    def setUp(self):
        self.rs1 = Raster("test/data/elevation_small.tif")
        self.rs1_np = self.rs1._rs.values
        self.rs2 = Raster("test/data/elevation2_small.tif")
        self.rs2_np = self.rs2._rs.values

    def tearDown(self):
        self.rs1.close()
        self.rs2.close()

    def test_eq(self):
        for v, vnp in [
            (self.rs2, self.rs2_np),
            (0, 0),
            (self.rs1_np[0, 10, 10], self.rs1_np[0, 10, 10]),
        ]:
            truth = self.rs1_np == vnp
            rst = self.rs1.eq(v)
            self.assertTrue(rs_eq_array(rst, truth))
            rst = self.rs1 == v
            self.assertTrue(rs_eq_array(rst, truth))

    def test_ne(self):
        for v, vnp in [
            (self.rs2, self.rs2_np),
            (0, 0),
            (self.rs1_np[0, 10, 10], self.rs1_np[0, 10, 10]),
        ]:
            truth = self.rs1_np != vnp
            rst = self.rs1.ne(v)
            self.assertTrue(rs_eq_array(rst, truth))
            rst = self.rs1 != v
            self.assertTrue(rs_eq_array(rst, truth))

    def test_le(self):
        for v, vnp in [
            (self.rs2, self.rs2_np),
            (0, 0),
            (self.rs1_np[0, 10, 10], self.rs1_np[0, 10, 10]),
        ]:
            truth = self.rs1_np <= vnp
            rst = self.rs1.le(v)
            self.assertTrue(rs_eq_array(rst, truth))
            rst = self.rs1 <= v
            self.assertTrue(rs_eq_array(rst, truth))

    def test_ge(self):
        for v, vnp in [
            (self.rs2, self.rs2_np),
            (0, 0),
            (self.rs1_np[0, 10, 10], self.rs1_np[0, 10, 10]),
        ]:
            truth = self.rs1_np >= vnp
            rst = self.rs1.ge(v)
            self.assertTrue(rs_eq_array(rst, truth))
            rst = self.rs1 >= v
            self.assertTrue(rs_eq_array(rst, truth))

    def test_lt(self):
        for v, vnp in [
            (self.rs2, self.rs2_np),
            (0, 0),
            (self.rs1_np[0, 10, 10], self.rs1_np[0, 10, 10]),
        ]:
            truth = self.rs1_np < vnp
            rst = self.rs1.lt(v)
            self.assertTrue(rs_eq_array(rst, truth))
            rst = self.rs1 < v
            self.assertTrue(rs_eq_array(rst, truth))

    def test_gt(self):
        for v, vnp in [
            (self.rs2, self.rs2_np),
            (0, 0),
            (self.rs1_np[0, 10, 10], self.rs1_np[0, 10, 10]),
        ]:
            truth = self.rs1_np > vnp
            rst = self.rs1.gt(v)
            self.assertTrue(rs_eq_array(rst, truth))
            rst = self.rs1 > v
            self.assertTrue(rs_eq_array(rst, truth))


class TestAstype(unittest.TestCase):
    def test_astype(self):
        rs = Raster("test/data/elevation_small.tif")
        for type_code, dtype in _DTYPE_INPUT_TO_DTYPE.items():
            self.assertEqual(rs.astype(type_code).dtype, dtype)
            self.assertEqual(rs.astype(type_code).eval().dtype, dtype)

    def test_wrong_type_codes(self):
        rs = Raster("test/data/elevation_small.tif")
        self.assertRaises(ValueError, lambda: rs.astype("not float32"))
        self.assertRaises(ValueError, lambda: rs.astype("other"))

    def test_dtype_property(self):
        rs = Raster("test/data/elevation_small.tif")
        self.assertEqual(rs.dtype, rs._rs.dtype)

    def test_astype_str_uppercase(self):
        rs = Raster("test/data/elevation_small.tif")
        for type_code, dtype in _DTYPE_INPUT_TO_DTYPE.items():
            if isinstance(type_code, str):
                type_code = type_code.upper()
                self.assertEqual(rs.astype(type_code).eval().dtype, dtype)


class TestRasterAttrs(unittest.TestCase):
    def test_arithmetic_attr_propagation(self):
        r1 = Raster("test/data/elevation.tif")
        true_attrs = r1._attrs
        v = 2.1
        for op in _BINARY_ARITHMETIC_OPS.keys():
            r2 = r1._binary_arithmetic(v, op).eval()
            self.assertEqual(r2._rs.attrs, true_attrs)
            self.assertEqual(r2._attrs, true_attrs)
        for r in [+r1, -r1]:
            self.assertEqual(r._rs.attrs, true_attrs)
            self.assertEqual(r._attrs, true_attrs)

    def test_ctor_attr_propagation(self):
        r1 = Raster("test/data/elevation.tif")
        true_attrs = r1._attrs.copy()
        r2 = Raster(Raster("test/data/elevation.tif"))
        test_attrs = {"test": 0}
        r3 = Raster("test/data/elevation.tif")
        r3._attrs = test_attrs
        self.assertEqual(r2._attrs, true_attrs)
        self.assertEqual(r3._attrs, test_attrs)

    def test_astype_attrs(self):
        rs = Raster("test/data/elevation_small.tif")
        attrs = rs._attrs
        self.assertEqual(rs.astype(I32)._attrs, attrs)


class TestCopy(unittest.TestCase):
    def test_copy(self):
        rs = Raster("test/data/elevation_small.tif")
        copy = rs.copy()
        self.assertIsNot(rs, copy)
        self.assertIsNot(rs._rs, copy._rs)
        self.assertIsNot(rs._attrs, copy._attrs)
        self.assertTrue((rs._rs == copy._rs).all())
        self.assertEqual(rs._attrs, copy._attrs)


class TestReplaceNull(unittest.TestCase):
    def test_replace_null(self):
        fill_value = 0
        rs = Raster("test/data/null_values.tiff")
        rsnp = rs._rs.values
        rsnp_replaced = rsnp.copy()
        rsnp_replaced[np.isnan(rsnp)] = fill_value
        rsnp_replaced[rsnp == rs._attrs["nodatavals"][0]] = fill_value
        rs = rs.replace_null(fill_value)
        self.assertTrue(rs_eq_array(rs, rsnp_replaced))


class TestRemapRange(unittest.TestCase):
    def test_remap_range(self):
        rs = Raster("test/data/elevation_small.tif")
        rsnp = rs._rs.values
        min, max, new_value = rs._rs.values.min(), rs._rs.values.max(), 0
        rng = (min, min + (0.2 * (max - min)))
        match = rsnp >= rng[0]
        match &= rsnp < rng[1]
        rsnp[match] = new_value
        rs = rs.remap_range(rng[0], rng[1], new_value)
        self.assertTrue(rs_eq_array(rs, rsnp))


class TestEval(unittest.TestCase):
    def test_eval(self):
        rs = Raster("test/data/elevation_small.tif")
        rsnp = rs._rs.values
        rs += 2
        rsnp += 2
        rs -= rs
        rsnp -= rsnp
        rs *= -1
        rsnp *= -1
        result = rs.eval()
        # Make sure new raster returned
        self.assertIsNot(rs, result)
        self.assertIsNot(rs._rs, result._rs)
        # Make sure that original raster is still lazy
        self.assertTrue(dask.is_dask_collection(rs._rs))
        self.assertTrue(rs_eq_array(result, rsnp))
        self.assertFalse(dask.is_dask_collection(result._rs))


class TestToLazy(unittest.TestCase):
    def test_to_lazy(self):
        rs = Raster("test/data/elevation2_small.tif")
        rs += rs
        rs_nonlazy = rs.eval()
        rs_lazy = rs_nonlazy.to_lazy()
        self.assertFalse(dask.is_dask_collection(rs_nonlazy._rs))
        self.assertTrue(dask.is_dask_collection(rs_lazy._rs))


if __name__ == "__main__":
    unittest.main()
