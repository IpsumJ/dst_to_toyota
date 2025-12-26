#!/usr/bin/env python
from embfile import EmbFile
import matplotlib.pyplot as plt
import sys


if len(sys.argv) < 3:
    print(f'Usage: {sys.argv[0]} input_file.dst output_file.10o')
    exit(1)

input_file = sys.argv[1]
output_file = sys.argv[2]

with open(input_file, 'rb') as f:
    input = f.read()

emb = EmbFile()

emb.load_dst(input)

for i,s in enumerate(emb._stitches):
    print(i, s)

print(emb.colors, 'Colors')

emb.plot()
plt.show()

output = emb.to10o()

with open(output_file, 'wb') as f:
    f.write(output)
