from enum import Enum
import matplotlib.pyplot as plt
import matplotlib.patches as patches

class StitchType(Enum):
    UNKNOWN = 0
    NORMAL = 1
    JUMP = 2
    COLORCHANGE = 3
    TRIM = 4

class Stitch():
    def __init__(self, dx = 0, dy = 0, t = StitchType.UNKNOWN) -> None:
        self.dx = dx
        self.dy = dy
        self.type = t

    def __str__(self) -> str:
        return f'{self.type.name}: dx: {self.dx}, dy: {self.dy}'

    def to10o(self) -> bytes:
        bx = abs(self.dx)
        by = abs(self.dy)
        bc = 0x80

        if self.dx < 0:
            bc |= (1 << 5)
        if self.dy < 0:
            bc |= (1 << 6)

        if self.type == StitchType.JUMP:
            bc |= (1 << 4)
        elif self.type == StitchType.COLORCHANGE:
            bc |= (1 << 2) | (1 << 0)
        elif self.type == StitchType.TRIM:
            bc |= (1 << 0)

        return bytes([bc, by, bx])

    @classmethod
    def from_dst(cls, dst_bytes: bytes) -> 'Stitch':
        s = cls()

        b1, b2, b3 = dst_bytes
        
        if (b3 & 0x03) != 0x03:
            raise ValueError('Allways set Bits not set')
        c = (b3 & 0xc0) >> 6
        if c == 0:
            s.type = StitchType.NORMAL
        elif c == 1:
            s.type = StitchType.UNKNOWN # SequinMode not supported
        elif c == 2:
            s.type = StitchType.JUMP
        elif c == 3:
            s.type = StitchType.COLORCHANGE
        
        def decode_byte(b):
            x, y, = 0, 0
            if b & (1 << 7):
                y += 1
            if b & (1 << 6):
                y -= 1
            if b & (1 << 5):
                y += 9
            if b & (1 << 4):
                y -= 9
            if b & (1 << 3):
                x -= 9
            if b & (1 << 2):
                x += 9
            if b & (1 << 1):
                x -= 1
            if b & (1 << 0):
                x += 1
            return x, y
        
        x, y = decode_byte(b1)
        b2_decoded = decode_byte(b2)
        x += b2_decoded[0] * 3
        y += b2_decoded[1] * 3
        b3_decoded = decode_byte(b3 & 0x3c)
        x += b3_decoded[0] * 3*3
        y += b3_decoded[1] * 3*3
        
        s.dx = x
        s.dy = y

        return s

class EmbFile():
    def __init__(self) -> None:
        self.colors = 0
        self._stitches = []

    def load_dst(self, dst_data: bytes) -> None:
        # reset state
        self.colors = 1
        self._stitches = []

        # header ignored at the moment
        header = dst_data[0:512]
        data = bytearray(dst_data[512:])

        # seperate into blocks and parse stitches.
        # DST does not support trim commands. Usualy
        # machines insert a trim after 3 consecutive jumps.
        # also count colorchange comands to thos 3? At least I
        # have seen one file that should be interpreted like this
        # If there where no Normal stitches since the last cut, dont add a cut command.
        # This prevents extra cuts on long movements.
        con_jump_cnt = 0
        normal_stitche_since_last_cut = False
        while len(data) >= 3:
            block = data[:3]
            del data[:3]
            self._stitches.append(Stitch.from_dst(block))

            if self._stitches[-1].type == StitchType.NORMAL:
                normal_stitche_since_last_cut = True

            if normal_stitche_since_last_cut and \
                (self._stitches[-1].type == StitchType.JUMP or \
                self._stitches[-1].type == StitchType.COLORCHANGE):
                con_jump_cnt += 1
                if con_jump_cnt >= 3:
                    self._stitches.insert(-3, Stitch(t = StitchType.TRIM))
                    normal_stitche_since_last_cut = False
                    con_jump_cnt = 0
            else:
                con_jump_cnt = 0

            if self._stitches[-1].type == StitchType.COLORCHANGE:
                self.colors += 1
        if self._stitches[-1].type == StitchType.COLORCHANGE:
            self._stitches[-1].type = StitchType.TRIM
            self.colors -= 1
        else:
            print('WARNING: Usualy dst files end with a color change. This one does not!')


    def to10o(self) -> bytes:
        out = b'\x8a\x00\x00'

        for s in self._stitches:
            out += s.to10o()

        out += b'\x87\x00\x00'
        return out

    def plot(self, ax=None):
        normal = '-x'
        nostitch = ':.'

        paths_x = [[0]]
        paths_y = [[0]]
        styles = [nostitch]
        colors = [0]
        for s in self._stitches:
            if s.type == StitchType.COLORCHANGE:
                if s.dx != 0 or s.dx != 0:
                    print('WARNING: Colorchange with x, y != 0!')
                paths_x.append([paths_x[-1][-1]])
                paths_y.append([paths_y[-1][-1]])
                styles.append(nostitch)
                colors.append(colors[-1] + 1)
                continue
            if s.type == StitchType.TRIM:
                paths_x.append([paths_x[-1][-1]])
                paths_y.append([paths_y[-1][-1]])
                styles.append(nostitch)
                colors.append(colors[-1])
            if s.type == StitchType.NORMAL and styles[-1] == nostitch:
                if len(paths_x[-1]) > 1:
                    paths_x.append([])
                    paths_y.append([])
                    styles.append(normal)
                    colors.append(colors[-1])
                else:
                    styles[-1] = normal
            if len(paths_x[-1]) == 0:
                paths_x[-1].append(paths_x[-2][-1] + s.dx * 0.1)
                paths_y[-1].append(paths_y[-2][-1] + s.dy * 0.1)
            else:
                paths_x[-1].append(paths_x[-1][-1] + s.dx * 0.1)
                paths_y[-1].append(paths_y[-1][-1] + s.dy * 0.1)

        cycle = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b',
            '#e377c2', '#7f7f7f', '#bcbd22', '#17becf', '#393b79', '#637939',
            '#8c6d31', '#843c39', '#7b4173', '#3182bd', '#31a354', '#756bb1',
            '#636363', '#e6550d', '#9c9ede', '#6baed6', '#bcbddc', '#9e9ac8'
        ]

        if ax is None:
            _, ax = plt.subplots(1, 1)
        for i,style in enumerate(styles):
            ax.plot(paths_x[i], paths_y[i], style, color = cycle[colors[i] % len(cycle)])

        # plot colors
        y_pos = -0.2
        square_size = 0.05
        margin = 0.02

        ax.figure.subplots_adjust(bottom=0.25)

        for i in set(colors):
            x_pos = i * (square_size + margin)
            rect = patches.Rectangle(
                (x_pos, y_pos), square_size, square_size,
                transform=ax.transAxes,     # use axes fraction coordinates (0–1 range)
                facecolor=cycle[i % len(cycle)],
                clip_on=False
            )
            ax.add_patch(rect)

        ax.set_aspect('equal')
        ax.grid(True)
        ax.set_title(f'{self.colors} Colors, {len(self._stitches)} Stitches')
