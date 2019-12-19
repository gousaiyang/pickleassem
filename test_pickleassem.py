import pickle
import sys
import unittest

from pickleassem import (HIGHEST_PROTOCOL, PROTO, Opcode, PickleAssembler,  # pylint: disable=unused-import
                         PickleProtocolMismatchError, _is_opcode_method, _method_name_to_opcode, p8, p16, p32, p64,
                         pack)

DEFAULT_TEST_PROTO = pickle.HIGHEST_PROTOCOL


class SampleClass:
    def __new__(cls, attr1=None, *, attr2=None):
        obj = super().__new__(cls)
        obj.attr1 = attr1
        obj.attr2 = attr2
        return obj

    def __eq__(self, other):
        return isinstance(other, SampleClass) and other.__dict__ == self.__dict__

    def __hash__(self):  # pragma: no cover
        return hash((self.attr1, self.attr2))


class TestPickleAssembler(unittest.TestCase):
    def test_init(self):
        with self.assertRaises(TypeError):
            pa = PickleAssembler(proto='x')
        with self.assertRaises(ValueError):
            pa = PickleAssembler(proto=-1)
        with self.assertRaises(ValueError):
            pa = PickleAssembler(proto=HIGHEST_PROTOCOL + 1)
        with self.assertRaises(TypeError):
            pa = PickleAssembler(proto=0, verify='x')

        pa = PickleAssembler(proto=2, verify=False)
        self.assertEqual(pa.proto, 2)
        self.assertEqual(pa.verify, False)
        self.assertEqual(pa._payload, PROTO + p8(2))  # pylint: disable=protected-access

        pa = PickleAssembler(proto=1)
        self.assertEqual(pa.proto, 1)
        self.assertEqual(pa.verify, True)
        self.assertEqual(pa._payload, b'')  # pylint: disable=protected-access

    def test_push_0(self):
        test_cases = [
            ('push_none', None),
            ('push_false', False),
            ('push_true', True),
            ('push_empty_tuple', ()),
            ('push_empty_list', []),
            ('push_empty_dict', {}),
            ('push_empty_set', set()),
        ]

        for test_case in test_cases:
            function, expected_result = test_case
            with self.subTest(test_case=test_case):
                pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
                getattr(pa, function)()
                self.assertEqual(pickle.loads(pa.assemble()), expected_result)

    def test_push_1(self):
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
        ]

        if DEFAULT_TEST_PROTO >= 5:  # pragma: no cover
            test_cases.append(('push_bytearray8', b'\xcc\xdd'))

        for test_case in test_cases:
            function, arg = test_case
            with self.subTest(test_case=test_case):
                pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
                getattr(pa, function)(arg)
                self.assertEqual(pickle.loads(pa.assemble()), arg)

    def test_push_global(self):
        pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
        pa.push_global('__main__', 'SampleClass')
        self.assertIs(pickle.loads(pa.assemble()), SampleClass)

    def test_build(self):
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
            self.assertEqual(pickle.loads(pa.assemble()), {1, 2, 3})

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

    def test_pop(self):
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

    def test_memo(self):
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
        pa.build_tuple()
        self.assertEqual(pickle.loads(pa.assemble()), (1, 2, 3, 4, 3, 3, 2, 4))

    def test_string_encoding(self):
        test_cases = [
            ('push_string', '\xcc', 'latin-1'),
            ('push_binstring', '\xcc', 'latin-1'),
            ('push_binstring', '\u4e2d\u6587', 'utf-8'),
            ('push_short_binstring', '\xcc', 'latin-1'),
            ('push_short_binstring', '\u4e2d\u6587', 'utf-8'),
        ]

        for test_case in test_cases:
            function, string, encoding = test_case
            with self.subTest(test_case=test_case):
                pa = PickleAssembler(proto=DEFAULT_TEST_PROTO)
                getattr(pa, function)(string, encoding)
                self.assertEqual(pickle.loads(pa.assemble(), encoding=encoding), string)

    def test_invalid_arg(self):
        test_cases = [
            ('push_int', ('x',), TypeError),
            ('push_binint', ('x',), TypeError),
            ('push_binint', (2 ** 31,), ValueError),
            ('push_binint', (- 2 ** 31 - 1,), ValueError),
            ('push_binint1', ('x',), TypeError),
            ('push_binint1', (-1,), ValueError),
            ('push_binint1', (2 ** 8,), ValueError),
            ('push_binint2', ('x',), TypeError),
            ('push_binint2', (-1,), ValueError),
            ('push_binint2', (2 ** 16,), ValueError),
            ('push_long', ('x',), TypeError),
            ('push_long1', ('x',), TypeError),
            ('push_long1', (2 ** 2039,), ValueError),
            ('push_long1', (- 2 ** 2039 - 1,), ValueError),
            ('push_long4', ('x',), TypeError),
            ('push_float', ('x',), TypeError),
            ('push_binfloat', ('x',), TypeError),
            ('push_string', (1,), TypeError),
            ('push_string', (b'x',), TypeError),
            ('push_string', ('x', 'x'), LookupError),
            ('push_binstring', (1,), TypeError),
            ('push_binstring', (b'x',), TypeError),
            ('push_binstring', ('x', 'x'), LookupError),
            ('push_short_binstring', (1,), TypeError),
            ('push_short_binstring', (b'x',), TypeError),
            ('push_short_binstring', ('x', 'x'), LookupError),
            ('push_short_binstring', ('A' * 256,), ValueError),
            ('push_binbytes', (1,), TypeError),
            ('push_binbytes', ('x',), TypeError),
            ('push_binbytes8', (1,), TypeError),
            ('push_binbytes8', ('x',), TypeError),
            ('push_short_binbytes', (1,), TypeError),
            ('push_short_binbytes', ('x',), TypeError),
            ('push_short_binbytes', (b'\xcc' * 256,), ValueError),
            ('push_bytearray8', (1,), TypeError),
            ('push_bytearray8', ('x',), TypeError),
            ('push_unicode', (1,), TypeError),
            ('push_unicode', (b'x',), TypeError),
            ('push_binunicode', (1,), TypeError),
            ('push_binunicode', (b'x',), TypeError),
            ('push_binunicode8', (1,), TypeError),
            ('push_binunicode8', (b'x',), TypeError),
            ('push_short_binunicode', (1,), TypeError),
            ('push_short_binunicode', (b'x',), TypeError),
            ('push_short_binunicode', ('A' * 256,), ValueError),
            ('push_global', (b'os', 'system'), TypeError),
            ('push_global', ('os', b'system'), TypeError),
            ('build_inst', (b'os', 'system'), TypeError),
            ('build_inst', ('os', b'system'), TypeError),
            ('memo_get', ('x',), TypeError),
            ('memo_get', (-1,), ValueError),
            ('memo_binget', ('x',), TypeError),
            ('memo_binget', (-1,), ValueError),
            ('memo_binget', (2 ** 8,), ValueError),
            ('memo_long_binget', ('x',), TypeError),
            ('memo_long_binget', (-1,), ValueError),
            ('memo_long_binget', (2 ** 32,), ValueError),
            ('memo_put', ('x',), TypeError),
            ('memo_put', (-1,), ValueError),
            ('memo_binput', ('x',), TypeError),
            ('memo_binput', (-1,), ValueError),
            ('memo_binput', (2 ** 8,), ValueError),
            ('memo_long_binput', ('x',), TypeError),
            ('memo_long_binput', (-1,), ValueError),
            ('memo_long_binput', (2 ** 32,), ValueError),
        ]

        for test_case in test_cases:
            function, args, error = test_case
            with self.subTest(test_case=test_case):
                pa = PickleAssembler(proto=DEFAULT_TEST_PROTO, verify=False)
                with self.assertRaises(error):
                    getattr(pa, function)(*args)

    def test_protocol_mismatch(self):
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
        ]

        for test_case in test_cases:
            function, args, proto = test_case
            with self.subTest(test_case=test_case):
                pa = PickleAssembler(proto=proto - 1)
                with self.assertRaises(PickleProtocolMismatchError):
                    getattr(pa, function)(*args)
                pa = PickleAssembler(proto=proto - 1, verify=False)
                getattr(pa, function)(*args)

    def test_packing(self):
        test_cases = [
            ('pack', 0, {'endian': '<', 'signed': True}, b''),
            ('pack', 255, {'endian': '<', 'signed': True}, b'\xff\x00'),
            ('pack', -256, {'endian': '<', 'signed': True}, b'\x00\xff'),
            ('pack', 32767, {'endian': '<', 'signed': True}, b'\xff\x7f'),
            ('pack', 32768, {'endian': '<', 'signed': True}, b'\x00\x80\x00'),
            ('pack', -32768, {'endian': '<', 'signed': True}, b'\x00\x80'),
            ('pack', -32769, {'endian': '<', 'signed': True}, b'\xff\x7f\xff'),
            ('pack', -128, {'endian': '<', 'signed': True}, b'\x80'),
            ('pack', -129, {'endian': '<', 'signed': True}, b'\x7f\xff'),
            ('pack', 127, {'endian': '<', 'signed': True}, b'\x7f'),
            ('pack', 128, {'endian': '<', 'signed': True}, b'\x80\x00'),
            ('pack', -32768, {'endian': '>', 'signed': True}, b'\x80\x00'),
            ('pack', 255, {'endian': '<'}, b'\xff'),
            ('p8', 0xbe, {}, b'\xbe'),
            ('p8', -128, {'signed': True}, b'\x80'),
            ('p16', 0xbeef, {}, b'\xef\xbe'),
            ('p16', -32768, {'signed': True}, b'\x00\x80'),
            ('p32', 0xdeadbeef, {}, b'\xef\xbe\xad\xde'),
            ('p32', - 2 ** 31, {'signed': True}, b'\x00\x00\x00\x80'),
            ('p64', 0xdeadbeefcafebabe, {}, b'\xbe\xba\xfe\xca\xef\xbe\xad\xde'),
            ('p64', - 2 ** 63, {'signed': True}, b'\x00\x00\x00\x00\x00\x00\x00\x80'),
        ]

        for test_case in test_cases:
            function, arg, kwargs, expected_result = test_case
            with self.subTest(test_case=test_case):
                self.assertEqual(globals()[function](arg, **kwargs), expected_result)

    def test_opcode_class(self):
        opcode = Opcode('NAME', b'\xcc', 5)
        self.assertEqual(opcode.name, 'NAME')
        self.assertEqual(opcode.code, b'\xcc')
        self.assertEqual(opcode.proto, 5)
        self.assertEqual(opcode, b'\xcc')
        self.assertEqual(opcode + b'\xdd', b'\xcc\xdd')
        self.assertEqual(b'\xdd' + opcode, b'\xdd\xcc')

    def test_is_opcode_method(self):
        self.assertTrue(_is_opcode_method('push_binbytes'))
        self.assertTrue(_is_opcode_method('build_tuple1'))
        self.assertTrue(_is_opcode_method('pop'))
        self.assertTrue(_is_opcode_method('memo_binput'))
        self.assertFalse(_is_opcode_method('__init__'))
        self.assertFalse(_is_opcode_method('assemble'))

    def test_method_name_to_opcode(self):
        opcode = _method_name_to_opcode('push_false')
        self.assertEqual(opcode.name, 'NEWFALSE')
        opcode = _method_name_to_opcode('push_true')
        self.assertEqual(opcode.name, 'NEWTRUE')
        opcode = _method_name_to_opcode('pop_mark')
        self.assertEqual(opcode.name, 'POP_MARK')
        opcode = _method_name_to_opcode('build_additems')
        self.assertEqual(opcode.name, 'ADDITEMS')
        opcode = _method_name_to_opcode('memo_long_binget')
        self.assertEqual(opcode.name, 'LONG_BINGET')
        opcode = _method_name_to_opcode('push_empty_dict')
        self.assertEqual(opcode.name, 'EMPTY_DICT')

    def test_method_decorator(self):
        self.assertEqual(PickleAssembler.build_append.__doc__, 'Corresponds to the APPEND opcode.')

    def test_exploit(self):
        pa = PickleAssembler(proto=0)
        pa.push_mark()
        pa.push_unicode('__import__("subprocess").check_output("echo hacked", shell=True, universal_newlines=True)')
        pa.build_inst('builtins', 'eval')
        payload = pa.assemble()
        self.assertNotIn(b'R', payload)
        self.assertEqual(pickle.loads(payload), 'hacked\n')


if __name__ == '__main__':
    sys.exit(unittest.main())
