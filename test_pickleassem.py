import pickle  # nosec
import re
import struct
import unittest
from typing import cast

from typing_extensions import TYPE_CHECKING

from pickleassem import (BINBYTES, BINFLOAT, BININT, BININT1, BININT2, BINUNICODE, DICT,  # nosec
                         EMPTY_DICT, EMPTY_LIST, EMPTY_TUPLE, FLOAT, HIGHEST_PROTOCOL, INT, LIST,
                         LONG1, LONG4, MARK, NEWFALSE, NONE, PROTO, SHORT_BINBYTES,
                         SHORT_BINUNICODE, TRUE, TUPLE, TUPLE1, TUPLE2, TUPLE3, UNICODE, Opcode,
                         PickleAssembler, PickleProtocolMismatchError, _is_opcode_method,
                         _method_name_to_opcode, p8, p16, p32, p64, pack)

if TYPE_CHECKING:
    from collections.abc import Callable

DEFAULT_TEST_PROTO = pickle.HIGHEST_PROTOCOL


class SampleClass:
    # Define attributes here for typing purposes.
    attr1 = None  # type: object
    attr2 = None  # type: object

    def __new__(cls, attr1: object = None, *, attr2: object = None) -> 'SampleClass':
        obj = super().__new__(cls)
        obj.attr1 = attr1
        obj.attr2 = attr2
        return cast(SampleClass, obj)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, SampleClass) and other.__dict__ == self.__dict__


class TestPickleAssembler(unittest.TestCase):
    def test_init(self) -> None:
        with self.assertRaisesRegex(TypeError, re.escape('pickle protocol must be an integer')):
            pa = PickleAssembler(proto='x')  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, re.escape('unsupported pickle protocol, must be in range')):
            pa = PickleAssembler(proto=-1)
        with self.assertRaisesRegex(ValueError, re.escape('unsupported pickle protocol, must be in range')):
            pa = PickleAssembler(proto=HIGHEST_PROTOCOL + 1)
        with self.assertRaisesRegex(TypeError, re.escape('verify must be bool')):
            pa = PickleAssembler(proto=0, verify='x')  # type: ignore[arg-type]

        pa = PickleAssembler(proto=2, verify=False)
        self.assertEqual(pa.proto, 2)
        self.assertFalse(pa.verify)
        self.assertEqual(pa._payload, PROTO + p8(2))  # pylint: disable=protected-access

        pa = PickleAssembler(proto=1)
        self.assertEqual(pa.proto, 1)
        self.assertTrue(pa.verify)
        self.assertEqual(pa._payload, b'')  # pylint: disable=protected-access

    def test_assemble(self) -> None:
        pa = PickleAssembler(proto=0)
        pa.push_none()
        self.assertEqual(pa.assemble(), NONE + b'.')

    def test_append_raw(self) -> None:
        pa = PickleAssembler(proto=0)
        pa.append_raw(b'foo')
        self.assertEqual(pa.assemble(), b'foo.')

        with self.assertRaisesRegex(TypeError, re.escape('raw data must be bytes')):
            pa.append_raw('string')  # type: ignore[arg-type]

    def test_push_0(self) -> None:
        test_cases = [
            ('push_none', None),
            ('push_false', False),
            ('push_true', True),
            ('push_empty_tuple', ()),
            ('push_empty_list', []),
            ('push_empty_dict', {}),
            ('push_empty_set', set()),
        ]  # type: list[tuple[str, object]]

        for test_case in test_cases:
            function, expected_result = test_case
            with self.subTest(test_case=test_case):
                pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
                getattr(pa, function)()
                self.assertEqual(pickle.loads(pa.assemble()), expected_result)

    def test_push_1(self) -> None:
        test_cases = [
            ('push_int', 66),
            ('push_int', False),
            ('push_int', True),
            ('push_binint', 2 ** 31 - 1),
            ('push_binint', - 2 ** 31),
            ('push_binint1', 0),
            ('push_binint1', 2 ** 8 - 1),
            ('push_binint2', 0),
            ('push_binint2', 2 ** 16 - 1),
            ('push_long', 0xdeadbeefcafebabe),
            ('push_long1', 2 ** 2039 - 1),
            ('push_long1', - 2 ** 2039),
            ('push_long4', -77),
            ('push_long4', 0xdeadbeefcafebabe),
            ('push_float', 3.14),
            ('push_binfloat', -1e1000),
            ('push_string', 'hello "world"\n'),
            ('push_binstring', 'hello "world"\n'),
            ('push_short_binstring', 'A' * 255),
            ('push_binbytes', b'\xcc\xdd'),
            ('push_binbytes8', b'\xcc\xdd'),
            ('push_short_binbytes', b'\xcc' * 255),
            ('push_unicode', 'hello "world"\n'),
            ('push_unicode', '\u4e2d\u6587'),
            ('push_binunicode', 'hello "world"\n'),
            ('push_binunicode', '\u4e2d\u6587'),
            ('push_binunicode8', 'hello "world"\n'),
            ('push_binunicode8', '\u4e2d\u6587'),
            ('push_short_binunicode', 'A' * 255),
            ('push_short_binunicode', '\u4e2d\u6587'),
        ]  # type: list[tuple[str, object]]

        if DEFAULT_TEST_PROTO >= 5:  # pragma: no cover
            test_cases.append(('push_bytearray8', bytearray(b'\xcc\xdd')))

        for test_case in test_cases:
            function, arg = test_case
            with self.subTest(test_case=test_case):
                pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
                getattr(pa, function)(arg)
                self.assertEqual(pickle.loads(pa.assemble()), arg)

    def test_push_global(self) -> None:
        pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
        pa.push_global('__main__', 'SampleClass')
        self.assertIs(pickle.loads(pa.assemble()), SampleClass)

    def test_build(self) -> None:
        with self.subTest(test_case='build_tuple'):
            pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
            pa.push_mark()
            pa.push_binint(1)
            pa.push_binint(2)
            pa.push_binint(3)
            pa.build_tuple()
            self.assertEqual(pickle.loads(pa.assemble()), (1, 2, 3))

        with self.subTest(test_case='build_tuple1'):
            pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
            pa.push_binint(1)
            pa.build_tuple1()
            self.assertEqual(pickle.loads(pa.assemble()), (1,))

        with self.subTest(test_case='build_tuple2'):
            pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
            pa.push_binint(1)
            pa.push_binint(2)
            pa.build_tuple2()
            self.assertEqual(pickle.loads(pa.assemble()), (1, 2))

        with self.subTest(test_case='build_tuple3'):
            pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
            pa.push_binint(1)
            pa.push_binint(2)
            pa.push_binint(3)
            pa.build_tuple3()
            self.assertEqual(pickle.loads(pa.assemble()), (1, 2, 3))

        with self.subTest(test_case='build_list'):
            pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
            pa.push_mark()
            pa.push_binint(1)
            pa.push_binint(2)
            pa.push_binint(3)
            pa.build_list()
            self.assertEqual(pickle.loads(pa.assemble()), [1, 2, 3])

        with self.subTest(test_case='build_dict'):
            pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
            pa.push_mark()
            pa.push_binint(1)
            pa.push_binint(2)
            pa.push_binint(3)
            pa.push_binint(4)
            pa.build_dict()
            self.assertEqual(pickle.loads(pa.assemble()), {1: 2, 3: 4})

        with self.subTest(test_case='build_frozenset'):
            pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
            pa.push_mark()
            pa.push_binint(1)
            pa.push_binint(2)
            pa.push_binint(3)
            pa.build_frozenset()
            result = pickle.loads(pa.assemble())
            self.assertEqual(result, frozenset({1, 2, 3}))
            self.assertIsInstance(result, frozenset)

        with self.subTest(test_case='build_append'):
            pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
            pa.push_mark()
            pa.push_binint(1)
            pa.push_binint(2)
            pa.build_list()
            pa.push_binint(3)
            pa.build_append()
            self.assertEqual(pickle.loads(pa.assemble()), [1, 2, 3])

        with self.subTest(test_case='build_appends'):
            pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
            pa.push_mark()
            pa.push_binint(1)
            pa.build_list()
            pa.push_mark()
            pa.push_binint(2)
            pa.push_binint(3)
            pa.build_appends()
            self.assertEqual(pickle.loads(pa.assemble()), [1, 2, 3])

        with self.subTest(test_case='build_setitem'):
            pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
            pa.push_mark()
            pa.push_binint(1)
            pa.push_binint(2)
            pa.build_dict()
            pa.push_binint(3)
            pa.push_binint(4)
            pa.build_setitem()
            self.assertEqual(pickle.loads(pa.assemble()), {1: 2, 3: 4})

        with self.subTest(test_case='build_setitems'):
            pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
            pa.push_mark()
            pa.push_binint(1)
            pa.push_binint(2)
            pa.build_dict()
            pa.push_mark()
            pa.push_binint(3)
            pa.push_binint(4)
            pa.push_binint(1)
            pa.push_binint(5)
            pa.build_setitems()
            self.assertEqual(pickle.loads(pa.assemble()), {1: 5, 3: 4})

        with self.subTest(test_case='build_additems'):
            pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
            pa.push_empty_set()
            pa.push_mark()
            pa.push_binint(1)
            pa.push_binint(2)
            pa.push_binint(3)
            pa.build_additems()
            result = pickle.loads(pa.assemble())
            self.assertEqual(result, {1, 2, 3})
            self.assertIsInstance(result, set)

        with self.subTest(test_case='build_inst'):
            pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
            pa.push_mark()
            pa.push_binunicode('foo')
            pa.build_inst('__main__', 'SampleClass')
            self.assertEqual(pickle.loads(pa.assemble()), SampleClass('foo'))

        with self.subTest(test_case='build_obj'):
            pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
            pa.push_mark()
            pa.push_global('__main__', 'SampleClass')
            pa.push_binunicode('foo')
            pa.build_obj()
            self.assertEqual(pickle.loads(pa.assemble()), SampleClass('foo'))

        with self.subTest(test_case='build_newobj'):
            pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
            pa.push_global('__main__', 'SampleClass')
            pa.push_binunicode('foo')
            pa.build_tuple1()
            pa.build_newobj()
            self.assertEqual(pickle.loads(pa.assemble()), SampleClass('foo'))

        with self.subTest(test_case='build_newobj_ex'):
            pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
            pa.push_global('__main__', 'SampleClass')
            pa.push_binunicode('foo')
            pa.build_tuple1()
            pa.push_mark()
            pa.push_binunicode('attr2')
            pa.push_binunicode('bar')
            pa.build_dict()
            pa.build_newobj_ex()
            self.assertEqual(pickle.loads(pa.assemble()), SampleClass('foo', attr2='bar'))

        with self.subTest(test_case='build_stack_global'):
            pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
            pa.push_binunicode('__main__')
            pa.push_binunicode('SampleClass')
            pa.build_stack_global()
            self.assertIs(pickle.loads(pa.assemble()), SampleClass)

        with self.subTest(test_case='build_reduce'):
            pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
            pa.push_global('__main__', 'SampleClass')
            pa.push_binunicode('foo')
            pa.build_tuple1()
            pa.build_reduce()
            self.assertEqual(pickle.loads(pa.assemble()), SampleClass('foo'))

        with self.subTest(test_case='build_build'):
            pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
            pa.push_global('__main__', 'SampleClass')
            pa.push_empty_tuple()
            pa.build_reduce()
            pa.push_mark()
            pa.push_binunicode('attr1')
            pa.push_binunicode('foo')
            pa.build_dict()
            pa.build_build()
            self.assertEqual(pickle.loads(pa.assemble()), SampleClass('foo'))

        with self.subTest(test_case='build_dup'):
            pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
            pa.push_mark()
            pa.push_binint(1)
            pa.build_dup()
            pa.build_tuple()
            self.assertEqual(pickle.loads(pa.assemble()), (1, 1))

    def test_pop(self) -> None:
        with self.subTest(test_case='pop'):
            pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
            pa.push_mark()
            pa.push_binint(1)
            pa.push_binint(2)
            pa.push_binint(3)
            pa.pop()
            pa.build_tuple()
            self.assertEqual(pickle.loads(pa.assemble()), (1, 2))

        with self.subTest(test_case='pop_mark'):
            pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
            pa.push_mark()
            pa.push_binint(1)
            pa.push_mark()
            pa.push_binint(2)
            pa.push_binint(3)
            pa.pop_mark()
            pa.build_tuple()
            self.assertEqual(pickle.loads(pa.assemble()), (1,))

    def test_memo(self) -> None:
        pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
        pa.push_mark()
        pa.push_binint(1)
        pa.memo_put(66)
        pa.push_binint(2)
        pa.memo_binput(255)
        pa.memo_binput(0)
        pa.push_binint(3)
        pa.memo_long_binput(0)
        pa.memo_long_binput(777)
        pa.push_binint(4)
        pa.memo_memoize()
        pa.memo_get(777)
        pa.memo_binget(0)
        pa.memo_binget(255)
        pa.memo_long_binget(4)
        pa.memo_binget(66)
        pa.build_tuple()
        self.assertEqual(pickle.loads(pa.assemble()), (1, 2, 3, 4, 3, 3, 2, 4, 1))

    def test_util_push(self) -> None:
        test_cases = [
            (None, 0, NONE + b'.'),
            (True, 1, TRUE + b'.'),
            (False, 2, PROTO + p8(2) + NEWFALSE + b'.'),
            (1, 0, INT + b'1\n.'),
            (255, 1, BININT1 + p8(255) + b'.'),
            (256, 1, BININT2 + p16(256) + b'.'),
            (65535, 1, BININT2 + p16(65535) + b'.'),
            (65536, 1, BININT + p32(65536, signed=True) + b'.'),
            (-1, 1, BININT + p32(-1, signed=True) + b'.'),
            (2 ** 31 - 1, 1, BININT + p32(2 ** 31 - 1, signed=True) + b'.'),
            (2 ** 31, 1, INT + b'2147483648\n.'),
            (2 ** 31, 2, PROTO + p8(2) + LONG1 + p8(5) + pack(2 ** 31, endian='<', signed=True) + b'.'),
            (2 ** 2039 - 1, 2, PROTO + p8(2) + LONG1 + p8(255) + pack(2 ** 2039 - 1, endian='<', signed=True) + b'.'),
            (2 ** 2039, 2, PROTO + p8(2) + LONG4 + p32(256) + pack(2 ** 2039, endian='<', signed=True) + b'.'),
            (2.1, 0, FLOAT + b'2.1\n.'),
            (2.1, 1, BINFLOAT + struct.pack('>d', 2.1) + b'.'),
            (b'foo', 3, PROTO + p8(3) + SHORT_BINBYTES + b'\x03foo.'),
            (b'x' * 255, 3, PROTO + p8(3) + SHORT_BINBYTES + p8(255) + b'x' * 255 + b'.'),
            (b'x' * 256, 3, PROTO + p8(3) + BINBYTES + p32(256) + b'x' * 256 + b'.'),
            ('bar\n\u4e2d\u6587', 0, UNICODE + br'bar\u000a\u4e2d\u6587' + b'\n.'),
            ('bar\n\u4e2d\u6587', 3, PROTO + p8(3) + BINUNICODE + p32(10) + b'bar\n\xe4\xb8\xad\xe6\x96\x87.'),
            ('bar\n\u4e2d\u6587', 4, PROTO + p8(4) + SHORT_BINUNICODE + p8(10) + b'bar\n\xe4\xb8\xad\xe6\x96\x87.'),
            ('x' * 256, 4, PROTO + p8(4) + BINUNICODE + p32(256) + b'x' * 256 + b'.'),
            ((), 0, MARK + TUPLE + b'.'),
            ((), 1, EMPTY_TUPLE + b'.'),
            ((1,), 1, MARK + BININT1 + p8(1) + TUPLE + b'.'),
            ((1,), 2, PROTO + p8(2) + BININT1 + p8(1) + TUPLE1 + b'.'),
            ((1, 2), 2, PROTO + p8(2) + BININT1 + p8(1) + BININT1 + p8(2) + TUPLE2 + b'.'),
            ((1, 2, 3), 2, PROTO + p8(2) + BININT1 + p8(1) + BININT1 + p8(2) + BININT1 + p8(3) + TUPLE3 + b'.'),
            ((1, 2, 3, 4), 2, PROTO + p8(2) + MARK + BININT1 + p8(1) + BININT1 + p8(2) + BININT1 + p8(3) + BININT1 + p8(4) + TUPLE + b'.'),  # noqa: E501  # pylint: disable=line-too-long
            ([], 0, MARK + LIST + b'.'),
            ([], 1, EMPTY_LIST + b'.'),
            ([1, 2], 1, MARK + BININT1 + p8(1) + BININT1 + p8(2) + LIST + b'.'),
            ({}, 0, MARK + DICT + b'.'),
            ({}, 1, EMPTY_DICT + b'.'),
            ({1: 2}, 1, MARK + BININT1 + p8(1) + BININT1 + p8(2) + DICT + b'.'),
        ]  # type: list[tuple[object, int, bytes]]

        for test_case in test_cases:
            arg, proto, expected_result = test_case
            with self.subTest(test_case=test_case):
                pa = PickleAssembler(proto=proto)
                pa.util_push(arg)
                result = pa.assemble()
                self.assertEqual(result, expected_result)
                self.assertEqual(pickle.loads(result), arg)

    def test_util_push_nested(self) -> None:
        obj = {(None, True): [{-1: 3.14}, 'boo']}
        for proto in range(DEFAULT_TEST_PROTO + 1):
            with self.subTest(obj=obj, proto=proto):
                pa = PickleAssembler(proto=proto)
                pa.util_push(obj)
                self.assertEqual(pickle.loads(pa.assemble()), obj)

        obj = {(None, True): [{-1: 3.14}, (b'baz', 'boo')]}
        for proto in range(3, DEFAULT_TEST_PROTO + 1):
            with self.subTest(obj=obj, proto=proto):
                pa = PickleAssembler(proto=proto)
                pa.util_push(obj)
                self.assertEqual(pickle.loads(pa.assemble()), obj)

    def test_util_push_bytes_min_proto(self) -> None:
        pa = PickleAssembler(proto=2)
        with self.assertRaisesRegex(PickleProtocolMismatchError,
                                    re.escape('must use at least protocol 3 to push bytes')):
            pa._util_push_bytes(b'x')  # pylint: disable=protected-access

    def test_util_memo(self) -> None:
        obj = (42,)
        indices = [255, 256]  # type: list[int]
        for proto in range(DEFAULT_TEST_PROTO + 1):
            for index in indices:
                with self.subTest(index=index, proto=proto):
                    pa = PickleAssembler(proto=proto)
                    pa.util_push(obj)
                    pa.util_memo_put(index)
                    pa.pop()
                    pa.util_memo_get(index)
                    self.assertEqual(pickle.loads(pa.assemble()), obj)

    def test_string_encoding(self) -> None:
        test_cases = [
            ('push_string', '\xcc', 'latin-1'),
            ('push_binstring', '\xcc', 'latin-1'),
            ('push_binstring', '\u4e2d\u6587', 'utf-8'),
            ('push_short_binstring', '\xcc', 'latin-1'),
            ('push_short_binstring', '\u4e2d\u6587', 'utf-8'),
        ]  # type: list[tuple[str, str, str]]

        for test_case in test_cases:
            function, string, encoding = test_case
            with self.subTest(test_case=test_case):
                pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
                getattr(pa, function)(string, encoding)
                self.assertEqual(pickle.loads(pa.assemble(), encoding=encoding), string)

    def test_invalid_arg(self) -> None:
        test_cases = [
            ('push_int', ('x',), TypeError, 'value should be an integer or bool'),
            ('push_binint', ('x',), TypeError, 'value should be an integer'),
            ('push_binint', (2 ** 31,), ValueError, 'integer out of range for opcode BININT'),
            ('push_binint', (- 2 ** 31 - 1,), ValueError, 'integer out of range for opcode BININT'),
            ('push_binint1', ('x',), TypeError, 'value should be an integer'),
            ('push_binint1', (-1,), ValueError, 'integer out of range for opcode BININT1'),
            ('push_binint1', (2 ** 8,), ValueError, 'integer out of range for opcode BININT1'),
            ('push_binint2', ('x',), TypeError, 'value should be an integer'),
            ('push_binint2', (-1,), ValueError, 'integer out of range for opcode BININT2'),
            ('push_binint2', (2 ** 16,), ValueError, 'integer out of range for opcode BININT2'),
            ('push_long', ('x',), TypeError, 'value should be an integer'),
            ('push_long1', ('x',), TypeError, 'value should be an integer'),
            ('push_long1', (2 ** 2039,), ValueError, 'integer too long for opcode LONG1'),
            ('push_long1', (- 2 ** 2039 - 1,), ValueError, 'integer too long for opcode LONG1'),
            ('push_long4', ('x',), TypeError, 'value should be an integer'),
            ('push_float', ('x',), TypeError, 'value should be a float'),
            ('push_binfloat', ('x',), TypeError, 'value should be a float'),
            ('push_string', (1,), TypeError, 'value should be str'),
            ('push_string', (b'x',), TypeError, 'value should be str'),
            ('push_string', ('x', 'x'), LookupError, 'unknown encoding'),
            ('push_binstring', (1,), TypeError, 'value should be str'),
            ('push_binstring', (b'x',), TypeError, 'value should be str'),
            ('push_binstring', ('x', 'x'), LookupError, 'unknown encoding'),
            ('push_short_binstring', (1,), TypeError, 'value should be str'),
            ('push_short_binstring', (b'x',), TypeError, 'value should be str'),
            ('push_short_binstring', ('x', 'x'), LookupError, 'unknown encoding'),
            ('push_short_binstring', ('A' * 256,), ValueError, 'string too long for opcode SHORT_BINSTRING'),
            ('push_binbytes', (1,), TypeError, 'value should be bytes'),
            ('push_binbytes', ('x',), TypeError, 'value should be bytes'),
            ('push_binbytes8', (1,), TypeError, 'value should be bytes'),
            ('push_binbytes8', ('x',), TypeError, 'value should be bytes'),
            ('push_short_binbytes', (1,), TypeError, 'value should be bytes'),
            ('push_short_binbytes', ('x',), TypeError, 'value should be bytes'),
            ('push_short_binbytes', (b'\xcc' * 256,), ValueError, 'bytes too long for opcode SHORT_BINBYTES'),
            ('push_unicode', (1,), TypeError, 'value should be str'),
            ('push_unicode', (b'x',), TypeError, 'value should be str'),
            ('push_binunicode', (1,), TypeError, 'value should be str'),
            ('push_binunicode', (b'x',), TypeError, 'value should be str'),
            ('push_binunicode8', (1,), TypeError, 'value should be str'),
            ('push_binunicode8', (b'x',), TypeError, 'value should be str'),
            ('push_short_binunicode', (1,), TypeError, 'value should be str'),
            ('push_short_binunicode', (b'x',), TypeError, 'value should be str'),
            ('push_short_binunicode', ('A' * 256,), ValueError, 'string too long for opcode SHORT_BINUNICODE'),
            ('push_global', (b'os', 'system'), TypeError, 'module and name should be str'),
            ('push_global', ('os', b'system'), TypeError, 'module and name should be str'),
            ('build_inst', (b'os', 'system'), TypeError, 'module and name should be str'),
            ('build_inst', ('os', b'system'), TypeError, 'module and name should be str'),
            ('memo_get', ('x',), TypeError, 'memo index should be an integer'),
            ('memo_get', (-1,), ValueError, 'memo index should be non-negative'),
            ('memo_binget', ('x',), TypeError, 'memo index should be an integer'),
            ('memo_binget', (-1,), ValueError, 'memo index out of range for opcode BINGET'),
            ('memo_binget', (2 ** 8,), ValueError, 'memo index out of range for opcode BINGET'),
            ('memo_long_binget', ('x',), TypeError, 'memo index should be an integer'),
            ('memo_long_binget', (-1,), ValueError, 'memo index out of range for opcode LONG_BINGET'),
            ('memo_long_binget', (2 ** 32,), ValueError, 'memo index out of range for opcode LONG_BINGET'),
            ('memo_put', ('x',), TypeError, 'memo index should be an integer'),
            ('memo_put', (-1,), ValueError, 'memo index should be non-negative'),
            ('memo_binput', ('x',), TypeError, 'memo index should be an integer'),
            ('memo_binput', (-1,), ValueError, 'memo index out of range for opcode BINPUT'),
            ('memo_binput', (2 ** 8,), ValueError, 'memo index out of range for opcode BINPUT'),
            ('memo_long_binput', ('x',), TypeError, 'memo index should be an integer'),
            ('memo_long_binput', (-1,), ValueError, 'memo index out of range for opcode LONG_BINPUT'),
            ('memo_long_binput', (2 ** 32,), ValueError, 'memo index out of range for opcode LONG_BINPUT'),
            ('_util_push_bool', (1,), TypeError, 'value should be a bool'),
            ('_util_push_int', (1.1,), TypeError, 'value should be an integer'),
            ('_util_push_float', ('x',), TypeError, 'value should be a float'),
            ('_util_push_bytes', ('x',), TypeError, 'value should be bytes'),
            ('_util_push_unicode', (b'x',), TypeError, 'value should be str'),
            ('_util_push_tuple', ([],), TypeError, 'value should be tuple'),
            ('_util_push_list', ((),), TypeError, 'value should be list'),
            ('_util_push_dict', ({0},), TypeError, 'value should be dict'),
            ('util_push', (frozenset(),), TypeError, 'is currently unsupported by `util_push`'),
            ('util_memo_get', ('x',), TypeError, 'memo index should be an integer'),
            ('util_memo_get', (-1,), ValueError, 'memo index should be non-negative'),
            ('util_memo_put', ('x',), TypeError, 'memo index should be an integer'),
            ('util_memo_put', (-1,), ValueError, 'memo index should be non-negative'),
        ]  # type: list[tuple[str, tuple[object, ...], type[BaseException], str]]

        if DEFAULT_TEST_PROTO >= 5:  # pragma: no cover
            test_cases += [
                ('push_bytearray8', (1,), TypeError, 'value should be bytes or bytearray'),
                ('push_bytearray8', ('x',), TypeError, 'value should be bytes or bytearray'),
            ]

        for test_case in test_cases:
            function, args, error, msg = test_case
            with self.subTest(test_case=test_case):
                pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
                with self.assertRaisesRegex(error, re.escape(msg)):
                    getattr(pa, function)(*args)

    def test_protocol_mismatch(self) -> None:
        test_cases = [
            ('push_binint', (1,), 1),
            ('push_binint1', (1,), 1),
            ('push_binint2', (1,), 1),
            ('push_binfloat', (1.1,), 1),
            ('push_binstring', ('x',), 1),
            ('push_short_binstring', ('x',), 1),
            ('push_binunicode', ('x',), 1),
            ('push_empty_tuple', (), 1),
            ('push_empty_list', (), 1),
            ('push_empty_dict', (), 1),
            ('build_appends', (), 1),
            ('build_setitems', (), 1),
            ('build_obj', (), 1),
            ('pop_mark', (), 1),
            ('memo_binget', (1,), 1),
            ('memo_long_binget', (1,), 1),
            ('memo_binput', (1,), 1),
            ('memo_long_binput', (1,), 1),
            ('push_false', (), 2),
            ('push_true', (), 2),
            ('push_long1', (1,), 2),
            ('push_long4', (1,), 2),
            ('build_tuple1', (), 2),
            ('build_tuple2', (), 2),
            ('build_tuple3', (), 2),
            ('build_newobj', (), 2),
            ('push_binbytes', (b'x',), 3),
            ('push_short_binbytes', (b'x',), 3),
            ('push_binbytes8', (b'x',), 4),
            ('push_binunicode8', ('x',), 4),
            ('push_short_binunicode', ('x',), 4),
            ('push_empty_set', (), 4),
            ('build_frozenset', (), 4),
            ('build_additems', (), 4),
            ('build_newobj_ex', (), 4),
            ('build_stack_global', (), 4),
            ('memo_memoize', (), 4),
            ('push_bytearray8', (b'x',), 5),
        ]  # type: list[tuple[str, tuple[object, ...], int]]

        for test_case in test_cases:
            function, args, proto = test_case
            with self.subTest(test_case=test_case):
                pa = PickleAssembler(proto=proto - 1)
                with self.assertRaisesRegex(PickleProtocolMismatchError,
                                            r'opcode (?:\w+?) requires protocol version >= (?:\d+?), '
                                            r'but current protocol is (?:\d+?)'):
                    getattr(pa, function)(*args)
                pa = PickleAssembler(proto=proto - 1, verify=False)
                getattr(pa, function)(*args)

    def test_packing(self) -> None:
        test_cases = [
            (pack, 0, {'endian': '<', 'signed': True}, b''),
            (pack, 255, {'endian': '<', 'signed': True}, b'\xff\x00'),
            (pack, -256, {'endian': '<', 'signed': True}, b'\x00\xff'),
            (pack, 32767, {'endian': '<', 'signed': True}, b'\xff\x7f'),
            (pack, 32768, {'endian': '<', 'signed': True}, b'\x00\x80\x00'),
            (pack, -32768, {'endian': '<', 'signed': True}, b'\x00\x80'),
            (pack, -32769, {'endian': '<', 'signed': True}, b'\xff\x7f\xff'),
            (pack, -128, {'endian': '<', 'signed': True}, b'\x80'),
            (pack, -129, {'endian': '<', 'signed': True}, b'\x7f\xff'),
            (pack, 127, {'endian': '<', 'signed': True}, b'\x7f'),
            (pack, 128, {'endian': '<', 'signed': True}, b'\x80\x00'),
            (pack, -32768, {'endian': '>', 'signed': True}, b'\x80\x00'),
            (pack, -32768, {'endian': 'big', 'signed': True}, b'\x80\x00'),
            (pack, 255, {'endian': '<'}, b'\xff'),
            (pack, 255, {'endian': 'little'}, b'\xff'),
            (pack, 255, {'endian': '<', 'word_size': 32}, b'\xff\x00\x00\x00'),
            (p8, 0xbe, {}, b'\xbe'),
            (p8, -128, {'signed': True}, b'\x80'),
            (p16, 0xbeef, {}, b'\xef\xbe'),
            (p16, -32768, {'signed': True}, b'\x00\x80'),
            (p32, 0xdeadbeef, {}, b'\xef\xbe\xad\xde'),
            (p32, - 2 ** 31, {'signed': True}, b'\x00\x00\x00\x80'),
            (p64, 0xdeadbeefcafebabe, {}, b'\xbe\xba\xfe\xca\xef\xbe\xad\xde'),
            (p64, - 2 ** 63, {'signed': True}, b'\x00\x00\x00\x00\x00\x00\x00\x80'),
        ]  # type: list[tuple[Callable[..., bytes], int, dict[str, object], bytes]]

        for test_case in test_cases:
            function, arg, kwargs, expected_result = test_case
            with self.subTest(test_case=test_case):
                self.assertEqual(function(arg, **kwargs), expected_result)

    def test_packing_invalid_args(self) -> None:
        test_cases = [
            (p8, -129, {'signed': True}, struct.error, ''),
            (p8, 128, {'signed': True}, struct.error, ''),
            (p8, -1, {}, struct.error, ''),
            (p8, 256, {}, struct.error, ''),
            (p16, -32769, {'signed': True}, struct.error, ''),
            (p16, 32768, {'signed': True}, struct.error, ''),
            (p16, -1, {}, struct.error, ''),
            (p16, 65536, {}, struct.error, ''),
            (p32, - 2 ** 31 - 1, {'signed': True}, struct.error, ''),
            (p32, 2 ** 31, {'signed': True}, struct.error, ''),
            (p32, -1, {}, struct.error, ''),
            (p32, 2 ** 32, {}, struct.error, ''),
            (p64, - 2 ** 63 - 1, {'signed': True}, struct.error, ''),
            (p64, 2 ** 63, {'signed': True}, struct.error, ''),
            (p64, -1, {}, struct.error, ''),
            (p64, 2 ** 64, {}, struct.error, ''),
            (pack, 0, {'endian': '?'}, ValueError, 'invalid endian'),
            (pack, 0, {'endian': '<', 'word_size': 3}, ValueError, 'invalid word size'),
        ]  # type: list[tuple[Callable[..., bytes], int, dict[str, object], type[BaseException], str]]

        for test_case in test_cases:
            function, arg, kwargs, error, msg = test_case
            with self.subTest(test_case=test_case):
                with self.assertRaisesRegex(error, re.escape(msg)):
                    function(arg, **kwargs)

    def test_opcode_class(self) -> None:
        opcode = Opcode('NAME', b'\xcc', 5)
        self.assertEqual(opcode.name, 'NAME')
        self.assertEqual(opcode.code, b'\xcc')
        self.assertEqual(opcode.proto, 5)
        self.assertEqual(opcode, b'\xcc')
        self.assertEqual(opcode + b'\xdd', b'\xcc\xdd')
        self.assertEqual(b'\xdd' + opcode, b'\xdd\xcc')

    def test_is_opcode_method(self) -> None:
        self.assertTrue(_is_opcode_method('push_false'))
        self.assertTrue(_is_opcode_method('push_binbytes'))
        self.assertTrue(_is_opcode_method('build_tuple1'))
        self.assertTrue(_is_opcode_method('pop'))
        self.assertTrue(_is_opcode_method('pop_mark'))
        self.assertTrue(_is_opcode_method('memo_binput'))
        self.assertFalse(_is_opcode_method('__init__'))
        self.assertFalse(_is_opcode_method('assemble'))
        self.assertFalse(_is_opcode_method('append_raw'))
        self.assertFalse(_is_opcode_method('_util_push_bool'))
        self.assertFalse(_is_opcode_method('util_push'))
        self.assertFalse(_is_opcode_method('util_memo_get'))

    def test_method_name_to_opcode(self) -> None:
        opcode = _method_name_to_opcode('push_false')
        self.assertEqual(opcode.name, 'NEWFALSE')
        opcode = _method_name_to_opcode('push_true')
        self.assertEqual(opcode.name, 'NEWTRUE')
        opcode = _method_name_to_opcode('pop')
        self.assertEqual(opcode.name, 'POP')
        opcode = _method_name_to_opcode('pop_mark')
        self.assertEqual(opcode.name, 'POP_MARK')
        opcode = _method_name_to_opcode('build_additems')
        self.assertEqual(opcode.name, 'ADDITEMS')
        opcode = _method_name_to_opcode('memo_long_binget')
        self.assertEqual(opcode.name, 'LONG_BINGET')
        opcode = _method_name_to_opcode('push_empty_dict')
        self.assertEqual(opcode.name, 'EMPTY_DICT')

    def test_method_decorator(self) -> None:
        self.assertEqual(PickleAssembler.build_append.__doc__, 'Corresponds to the ``APPEND`` opcode.')

    def test_exploit(self) -> None:
        pa = PickleAssembler(proto=0)
        pa.push_mark()
        pa.util_push('__import__("subprocess").check_output("echo hacked", shell=True, universal_newlines=True)')
        pa.build_inst('builtins', 'eval')
        payload = pa.assemble()
        self.assertNotIn(b'R', payload)
        self.assertEqual(pickle.loads(payload), 'hacked\n')


if __name__ == '__main__':
    unittest.main()
