import functools
import struct

# Integer packing utilities.

_endian_dict = {
    '<': 'little',
    '>': 'big',
    'little': 'little',
    'big': 'big'
}

_word_size_dict = {
    None: None,
    8: 'b',
    16: 'h',
    32: 'i',
    64: 'q'
}


def pack(x, *, endian, word_size=None, signed=False):
    if endian not in _endian_dict:  # pragma: no cover
        raise ValueError('invalid endian')
    if word_size not in _word_size_dict:  # pragma: no cover
        raise ValueError('invalid word size')
    endian = _endian_dict[endian]
    word_size = _word_size_dict[word_size]
    signed = bool(signed)
    if word_size is None:  # automatically determine byte length
        if signed:  # adapted from pickle.encode_long()
            if x == 0:
                return b''
            nbytes = (x.bit_length() >> 3) + 1
            result = x.to_bytes(nbytes, byteorder='little', signed=True)
            if x < 0 and nbytes > 1:
                if result[-1] == 0xff and (result[-2] & 0x80) != 0:
                    result = result[:-1]
            return result if endian == 'little' else result[::-1]
        else:
            return x.to_bytes((x.bit_length() + 7) >> 3, byteorder=endian, signed=False)
    if not signed:
        word_size = word_size.upper()
    endian = '<' if endian == 'little' else '>'
    return struct.pack(endian + word_size, x)


# Helper functions to pack integers.
# In pickle protocol, integers are always packed in little endian.
p8 = functools.partial(pack, word_size=8, endian='<')
p16 = functools.partial(pack, word_size=16, endian='<')
p32 = functools.partial(pack, word_size=32, endian='<')
p64 = functools.partial(pack, word_size=64, endian='<')

# The highest protocol number that we can generate.
HIGHEST_PROTOCOL = 5


class Opcode(bytes):
    def __new__(cls, name, code, proto):
        obj = super().__new__(cls, code)
        obj.name = name
        obj.code = code
        obj.proto = proto
        return obj


# Pickle opcodes from pickle.py

# Protocol 0 (text mode)

MARK             = Opcode('MARK',             b'(',    0)  # push special markobject on stack
STOP             = Opcode('STOP',             b'.',    0)  # every pickle ends with STOP
POP              = Opcode('POP',              b'0',    0)  # discard topmost stack item
DUP              = Opcode('DUP',              b'2',    0)  # duplicate top stack item
FLOAT            = Opcode('FLOAT',            b'F',    0)  # push float object; decimal string argument
INT              = Opcode('INT',              b'I',    0)  # push integer or bool; decimal string argument
LONG             = Opcode('LONG',             b'L',    0)  # push long; decimal string argument
NONE             = Opcode('NONE',             b'N',    0)  # push None
PERSID           = Opcode('PERSID',           b'P',    0)  # push persistent object; id is taken from string arg
REDUCE           = Opcode('REDUCE',           b'R',    0)  # apply callable to argtuple, both on stack
STRING           = Opcode('STRING',           b'S',    0)  # push string; NL-terminated string argument
UNICODE          = Opcode('UNICODE',          b'V',    0)  # push Unicode string; raw-unicode-escaped'd argument
APPEND           = Opcode('APPEND',           b'a',    0)  # append stack top to list below it
BUILD            = Opcode('BUILD',            b'b',    0)  # call __setstate__ or __dict__.update()
GLOBAL           = Opcode('GLOBAL',           b'c',    0)  # push self.find_class(modname, name); 2 string args
DICT             = Opcode('DICT',             b'd',    0)  # build a dict from stack items
GET              = Opcode('GET',              b'g',    0)  # push item from memo on stack; index is string arg
INST             = Opcode('INST',             b'i',    0)  # build & push class instance
LIST             = Opcode('LIST',             b'l',    0)  # build list from topmost stack items
PUT              = Opcode('PUT',              b'p',    0)  # store stack top in memo; index is string arg
SETITEM          = Opcode('SETITEM',          b's',    0)  # add key+value pair to dict
TUPLE            = Opcode('TUPLE',            b't',    0)  # build tuple from topmost stack items

TRUE             =                            b'I01\n'     # not an opcode; see INT docs in pickletools.py
FALSE            =                            b'I00\n'     # not an opcode; see INT docs in pickletools.py

# Protocol 1

POP_MARK         = Opcode('POP_MARK',         b'1',    1)  # discard stack top through topmost markobject
BININT           = Opcode('BININT',           b'J',    1)  # push four-byte signed int
BININT1          = Opcode('BININT1',          b'K',    1)  # push 1-byte unsigned int
BININT2          = Opcode('BININT2',          b'M',    1)  # push 2-byte unsigned int
BINPERSID        = Opcode('BINPERSID',        b'Q',    1)  # push persistent object; id is taken from stack
BINSTRING        = Opcode('BINSTRING',        b'T',    1)  # push string; counted binary string argument
SHORT_BINSTRING  = Opcode('SHORT_BINSTRING',  b'U',    1)  #  "     "   ;    "      "       "      " < 256 bytes
BINUNICODE       = Opcode('BINUNICODE',       b'X',    1)  # push Unicode string; counted UTF-8 string argument
EMPTY_DICT       = Opcode('EMPTY_DICT',       b'}',    1)  # push empty dict
APPENDS          = Opcode('APPENDS',          b'e',    1)  # extend list on stack by topmost stack slice
BINGET           = Opcode('BINGET',           b'h',    1)  # push item from memo on stack; index is 1-byte arg
LONG_BINGET      = Opcode('LONG_BINGET',      b'j',    1)  #   "    "    "    "   "   "  ;   "    " 4-byte arg
EMPTY_LIST       = Opcode('EMPTY_LIST',       b']',    1)  # push empty list
OBJ              = Opcode('OBJ',              b'o',    1)  # build & push class instance
BINPUT           = Opcode('BINPUT',           b'q',    1)  # store stack top in memo; index is 1-byte arg
LONG_BINPUT      = Opcode('LONG_BINPUT',      b'r',    1)  #   "     "    "   "   " ;   "    " 4-byte arg
EMPTY_TUPLE      = Opcode('EMPTY_TUPLE',      b')',    1)  # push empty tuple
SETITEMS         = Opcode('SETITEMS',         b'u',    1)  # modify dict by adding topmost key+value pairs
BINFLOAT         = Opcode('BINFLOAT',         b'G',    1)  # push float; arg is 8-byte float encoding

# Protocol 2 (Python 2.3+)

PROTO            = Opcode('PROTO',            b'\x80', 2)  # identify pickle protocol
NEWOBJ           = Opcode('NEWOBJ',           b'\x81', 2)  # build object by applying cls.__new__ to argtuple
EXT1             = Opcode('EXT1',             b'\x82', 2)  # push object from extension registry; 1-byte index
EXT2             = Opcode('EXT2',             b'\x83', 2)  # ditto, but 2-byte index
EXT4             = Opcode('EXT4',             b'\x84', 2)  # ditto, but 4-byte index
TUPLE1           = Opcode('TUPLE1',           b'\x85', 2)  # build 1-tuple from stack top
TUPLE2           = Opcode('TUPLE2',           b'\x86', 2)  # build 2-tuple from two topmost stack items
TUPLE3           = Opcode('TUPLE3',           b'\x87', 2)  # build 3-tuple from three topmost stack items
NEWTRUE          = Opcode('NEWTRUE',          b'\x88', 2)  # push True
NEWFALSE         = Opcode('NEWFALSE',         b'\x89', 2)  # push False
LONG1            = Opcode('LONG1',            b'\x8a', 2)  # push long from < 256 bytes
LONG4            = Opcode('LONG4',            b'\x8b', 2)  # push really big long

# Protocol 3 (Python 3.0+)

BINBYTES         = Opcode('BINBYTES',         b'B',    3)  # push bytes; counted binary string argument
SHORT_BINBYTES   = Opcode('SHORT_BINBYTES',   b'C',    3)  #  "     "   ;    "      "       "      " < 256 bytes

# Protocol 4 (Python 3.4+)

SHORT_BINUNICODE = Opcode('SHORT_BINUNICODE', b'\x8c', 4)  # push short string; UTF-8 length < 256 bytes
BINUNICODE8      = Opcode('BINUNICODE8',      b'\x8d', 4)  # push very long string
BINBYTES8        = Opcode('BINBYTES8',        b'\x8e', 4)  # push very long bytes string
EMPTY_SET        = Opcode('EMPTY_SET',        b'\x8f', 4)  # push empty set on the stack
ADDITEMS         = Opcode('ADDITEMS',         b'\x90', 4)  # modify set by adding topmost stack items
FROZENSET        = Opcode('FROZENSET',        b'\x91', 4)  # build frozenset from topmost stack items
NEWOBJ_EX        = Opcode('NEWOBJ_EX',        b'\x92', 4)  # like NEWOBJ but work with keyword only arguments
STACK_GLOBAL     = Opcode('STACK_GLOBAL',     b'\x93', 4)  # same as GLOBAL but using names on the stacks
MEMOIZE          = Opcode('MEMOIZE',          b'\x94', 4)  # store top of the stack in memo
FRAME            = Opcode('FRAME',            b'\x95', 4)  # indicate the beginning of a new frame

# Protocol 5 (Python 3.8+)

BYTEARRAY8       = Opcode('BYTEARRAY8',       b'\x96', 5)  # push bytearray
NEXT_BUFFER      = Opcode('NEXT_BUFFER',      b'\x97', 5)  # push next out-of-band buffer
READONLY_BUFFER  = Opcode('READONLY_BUFFER',  b'\x98', 5)  # make top of stack readonly


class PickleAssembler:
    """Pickle assembler."""
    def __init__(self, proto=0, verify=True):
        """Create a new pickle assembler.

        Args:
        - `proto` -- `int`, the protocol version to generate, a protocol header will be generated if proto >= 2
        - `verify` -- `bool`, whether to check opcodes against the protocol number

        """
        if not isinstance(proto, int):
            raise TypeError('pickle protocol must be an integer')
        if not 0 <= proto <= HIGHEST_PROTOCOL:
            raise ValueError('unsupported pickle protocol, must be in range [0, {}]'.format(HIGHEST_PROTOCOL))
        if not isinstance(verify, bool):
            raise TypeError('verify must be bool')
        self.proto = proto
        self.verify = verify
        self._payload = b''
        if proto >= 2:
            self._payload += PROTO + p8(proto)

    def assemble(self):
        """Assemble pickle payload.

        Returns:
        - `bytes` -- the generated pickle payload

        """
        return self._payload + STOP

    def push_none(self):
        self._payload += NONE

    def push_false(self):
        self._payload += NEWFALSE

    def push_true(self):
        self._payload += NEWTRUE

    def push_int(self, value):
        if isinstance(value, bool):
            self._payload += [FALSE, TRUE][value]
        elif isinstance(value, int):
            self._payload += INT + str(value).encode('ascii') + b'\n'
        else:
            raise TypeError('value should be an integer or bool')

    def push_binint(self, value):
        if not isinstance(value, int):
            raise TypeError('value should be an integer')
        if not - 2 ** 31 <= value <= 2 ** 31 - 1:
            raise ValueError('integer out of range for opcode BININT')
        self._payload += BININT + p32(value, signed=True)

    def push_binint1(self, value):
        if not isinstance(value, int):
            raise TypeError('value should be an integer')
        if not 0 <= value <= 2 ** 8 - 1:
            raise ValueError('integer out of range for opcode BININT1')
        self._payload += BININT1 + p8(value)

    def push_binint2(self, value):
        if not isinstance(value, int):
            raise TypeError('value should be an integer')
        if not 0 <= value <= 2 ** 16 - 1:
            raise ValueError('integer out of range for opcode BININT2')
        self._payload += BININT2 + p16(value)

    def push_long(self, value):
        if not isinstance(value, int):
            raise TypeError('value should be an integer')
        self._payload += LONG + str(value).encode('ascii') + b'\n'

    def push_long1(self, value):
        if not isinstance(value, int):
            raise TypeError('value should be an integer')
        value_bytes = pack(value, endian='<', signed=True)
        if len(value_bytes) >= 2 ** 8:
            raise ValueError('integer too long for opcode LONG1')
        self._payload += LONG1 + p8(len(value_bytes)) + value_bytes

    def push_long4(self, value):
        if not isinstance(value, int):
            raise TypeError('value should be an integer')
        value_bytes = pack(value, endian='<', signed=True)
        if len(value_bytes) >= 2 ** 31:  # pragma: no cover
            raise ValueError('integer too long for opcode LONG4')
        self._payload += LONG4 + p32(len(value_bytes), signed=True) + value_bytes

    def push_float(self, value):
        if not isinstance(value, float):
            raise TypeError('value should be a float')
        self._payload += FLOAT + str(value).encode('ascii') + b'\n'

    def push_binfloat(self, value):
        if not isinstance(value, float):
            raise TypeError('value should be a float')
        self._payload += BINFLOAT + struct.pack('>d', value)

    def push_string(self, value, encoding='ascii'):
        if not isinstance(value, str):
            raise TypeError('value should be str')
        self._payload += STRING + ascii(value).encode(encoding) + b'\n'

    def push_binstring(self, value, encoding='ascii'):
        if not isinstance(value, str):
            raise TypeError('value should be str')
        value_bytes = value.encode(encoding)
        if len(value_bytes) >= 2 ** 31:  # pragma: no cover
            raise ValueError('string too long for opcode BINSTRING')
        self._payload += BINSTRING + p32(len(value_bytes), signed=True) + value_bytes

    def push_short_binstring(self, value, encoding='ascii'):
        if not isinstance(value, str):
            raise TypeError('value should be str')
        value_bytes = value.encode(encoding)
        if len(value_bytes) >= 2 ** 8:
            raise ValueError('string too long for opcode SHORT_BINSTRING')
        self._payload += SHORT_BINSTRING + p8(len(value_bytes)) + value_bytes

    def push_binbytes(self, value):
        if not isinstance(value, bytes):
            raise TypeError('value should be bytes')
        if len(value) >= 2 ** 32:  # pragma: no cover
            raise ValueError('bytes too long for opcode BINBYTES')
        self._payload += BINBYTES + p32(len(value)) + value

    def push_binbytes8(self, value):
        if not isinstance(value, bytes):
            raise TypeError('value should be bytes')
        if len(value) >= 2 ** 64:  # pragma: no cover
            raise ValueError('bytes too long for opcode BINBYTES8')
        self._payload += BINBYTES8 + p64(len(value)) + value

    def push_short_binbytes(self, value):
        if not isinstance(value, bytes):
            raise TypeError('value should be bytes')
        if len(value) >= 2 ** 8:
            raise ValueError('bytes too long for opcode SHORT_BINBYTES')
        self._payload += SHORT_BINBYTES + p8(len(value)) + value

    def push_bytearray8(self, value):
        if not isinstance(value, bytes):
            raise TypeError('value should be bytes')
        if len(value) >= 2 ** 64:  # pragma: no cover
            raise ValueError('bytes too long for opcode BYTEARRAY8')
        self._payload += BYTEARRAY8 + p64(len(value)) + value

    def push_unicode(self, value):
        if not isinstance(value, str):
            raise TypeError('value should be str')
        value = value.replace('\\', '\\u005c')
        value = value.replace('\0', '\\u0000')
        value = value.replace('\n', '\\u000a')
        value = value.replace('\r', '\\u000d')
        value = value.replace('\x1a', '\\u001a')
        self._payload += UNICODE + value.encode('raw-unicode-escape') + b'\n'

    def push_binunicode(self, value):
        if not isinstance(value, str):
            raise TypeError('value should be str')
        value_bytes = value.encode('utf-8', 'surrogatepass')
        if len(value_bytes) >= 2 ** 32:  # pragma: no cover
            raise ValueError('string too long for opcode BINUNICODE')
        self._payload += BINUNICODE + p32(len(value_bytes)) + value_bytes

    def push_binunicode8(self, value):
        if not isinstance(value, str):
            raise TypeError('value should be str')
        value_bytes = value.encode('utf-8', 'surrogatepass')
        if len(value_bytes) >= 2 ** 64:  # pragma: no cover
            raise ValueError('string too long for opcode BINUNICODE8')
        self._payload += BINUNICODE8 + p64(len(value_bytes)) + value_bytes

    def push_short_binunicode(self, value):
        if not isinstance(value, str):
            raise TypeError('value should be str')
        value_bytes = value.encode('utf-8', 'surrogatepass')
        if len(value_bytes) >= 2 ** 8:
            raise ValueError('string too long for opcode SHORT_BINUNICODE')
        self._payload += SHORT_BINUNICODE + p8(len(value_bytes)) + value_bytes

    def push_empty_tuple(self):
        self._payload += EMPTY_TUPLE

    def push_empty_list(self):
        self._payload += EMPTY_LIST

    def push_empty_dict(self):
        self._payload += EMPTY_DICT

    def push_empty_set(self):
        self._payload += EMPTY_SET

    def push_global(self, module, name):
        if not isinstance(module, str) or not isinstance(name, str):
            raise TypeError('module and name should be str')
        self._payload += GLOBAL
        self._payload += module.encode('utf-8') + b'\n'
        self._payload += name.encode('utf-8') + b'\n'

    def push_mark(self):
        self._payload += MARK

    def build_tuple(self):
        self._payload += TUPLE

    def build_tuple1(self):
        self._payload += TUPLE1

    def build_tuple2(self):
        self._payload += TUPLE2

    def build_tuple3(self):
        self._payload += TUPLE3

    def build_list(self):
        self._payload += LIST

    def build_dict(self):
        self._payload += DICT

    def build_frozenset(self):
        self._payload += FROZENSET

    def build_append(self):
        self._payload += APPEND

    def build_appends(self):
        self._payload += APPENDS

    def build_setitem(self):
        self._payload += SETITEM

    def build_setitems(self):
        self._payload += SETITEMS

    def build_additems(self):
        self._payload += ADDITEMS

    def build_inst(self, module, name):
        if not isinstance(module, str) or not isinstance(name, str):
            raise TypeError('module and name should be str')
        self._payload += INST
        self._payload += module.encode('ascii') + b'\n'
        self._payload += name.encode('ascii') + b'\n'

    def build_obj(self):
        self._payload += OBJ

    def build_newobj(self):
        self._payload += NEWOBJ

    def build_newobj_ex(self):
        self._payload += NEWOBJ_EX

    def build_stack_global(self):
        self._payload += STACK_GLOBAL

    def build_reduce(self):
        self._payload += REDUCE

    def build_build(self):
        self._payload += BUILD

    def build_dup(self):
        self._payload += DUP

    def pop(self):
        self._payload += POP

    def pop_mark(self):
        self._payload += POP_MARK

    def memo_get(self, index):
        if not isinstance(index, int):
            raise TypeError('memo index should be an integer')
        if index < 0:
            raise ValueError('memo index should be non-negative')
        self._payload += GET + str(index).encode('ascii') + b'\n'

    def memo_binget(self, index):
        if not isinstance(index, int):
            raise TypeError('memo index should be an integer')
        if not 0 <= index <= 2 ** 8 - 1:
            raise ValueError('memo index out of range for opcode BINGET')
        self._payload += BINGET + p8(index)

    def memo_long_binget(self, index):
        if not isinstance(index, int):
            raise TypeError('memo index should be an integer')
        if not 0 <= index <= 2 ** 32 - 1:
            raise ValueError('memo index out of range for opcode LONG_BINGET')
        self._payload += LONG_BINGET + p32(index)

    def memo_put(self, index):
        if not isinstance(index, int):
            raise TypeError('memo index should be an integer')
        if index < 0:
            raise ValueError('memo index should be non-negative')
        self._payload += PUT + str(index).encode('ascii') + b'\n'

    def memo_binput(self, index):
        if not isinstance(index, int):
            raise TypeError('memo index should be an integer')
        if not 0 <= index <= 2 ** 8 - 1:
            raise ValueError('memo index out of range for opcode BINPUT')
        self._payload += BINPUT + p8(index)

    def memo_long_binput(self, index):
        if not isinstance(index, int):
            raise TypeError('memo index should be an integer')
        if not 0 <= index <= 2 ** 32 - 1:
            raise ValueError('memo index out of range for opcode LONG_BINPUT')
        self._payload += LONG_BINPUT + p32(index)

    def memo_memoize(self):
        self._payload += MEMOIZE


class PickleProtocolMismatchError(Exception):
    """Raised when opcode does not match protocol."""
    pass


# Internal operations.

def _is_opcode_method(method_name):
    return any(method_name.startswith(prefix) for prefix in ('push', 'build', 'pop', 'memo'))


def _method_name_to_opcode(method_name):
    if method_name in ('push_false', 'push_true'):
        return globals()['NEW' + method_name[5:].upper()]
    elif method_name.startswith('pop'):
        return globals()[method_name.upper()]
    elif method_name.startswith('build'):
        return globals()[method_name[6:].upper()]
    else:  # other push and memo
        return globals()[method_name[5:].upper()]


def _opcode_method_decorator(func):
    opcode = _method_name_to_opcode(func.__name__)
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.verify and self.proto < opcode.proto:
            raise PickleProtocolMismatchError('opcode {} requires protocol version >= {}, '
                                              'but current protocol is {}'.format(opcode.name, opcode.proto, self.proto))
        return func(self, *args, **kwargs)
    wrapper.__doc__ = 'Corresponds to the {} opcode.'.format(opcode.name)
    return wrapper


for method_name in dir(PickleAssembler):
    if _is_opcode_method(method_name):
        method = getattr(PickleAssembler, method_name)
        setattr(PickleAssembler, method_name, _opcode_method_decorator(method))

del method_name, method

__all__ = ['PickleAssembler', 'PickleProtocolMismatchError', 'HIGHEST_PROTOCOL']
