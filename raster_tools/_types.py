import numpy as np


U8 = np.dtype(np.uint8)
U16 = np.dtype(np.uint16)
U32 = np.dtype(np.uint32)
U64 = np.dtype(np.uint64)
I8 = np.dtype(np.int8)
I16 = np.dtype(np.int16)
I32 = np.dtype(np.int32)
I64 = np.dtype(np.int64)
F16 = np.dtype(np.float16)
F32 = np.dtype(np.float32)
F64 = np.dtype(np.float64)
# Some machines don't support np.float128 so use longdouble instead. This
# aliases f128 on machines that support it and f64 on machines that don't
F128 = np.dtype(np.longdouble)
BOOL = np.dtype(bool)
DTYPE_INPUT_TO_DTYPE = {
    # Unsigned int
    U8: U8,
    "uint8": U8,
    np.dtype("uint8"): U8,
    U16: U16,
    "uint16": U16,
    np.dtype("uint16"): U16,
    U32: U32,
    "uint32": U32,
    np.dtype("uint32"): U32,
    U64: U64,
    "uint64": U64,
    np.dtype("uint64"): U64,
    # Signed int
    I8: I8,
    "int8": I8,
    np.dtype("int8"): I8,
    I16: I16,
    "int16": I16,
    np.dtype("int16"): I16,
    I32: I32,
    "int32": I32,
    np.dtype("int32"): I32,
    I64: I64,
    "int64": I64,
    np.dtype("int64"): I64,
    int: I64,
    "int": I64,
    # Float
    F16: F16,
    "float16": F16,
    np.dtype("float16"): F16,
    F32: F32,
    "float32": F32,
    np.dtype("float32"): F32,
    F64: F64,
    "float64": F64,
    np.dtype("float64"): F64,
    F128: F128,
    "float128": F128,
    np.dtype("longdouble"): F128,
    float: F64,
    "float": F64,
    # Boolean
    BOOL: BOOL,
    bool: BOOL,
    "bool": BOOL,
    np.dtype("bool"): BOOL,
}