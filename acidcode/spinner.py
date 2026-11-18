from __future__ import annotations

from textual.widgets import Static

# Корпус планеты: все строки ровно 19 символов, чтобы кадры не дёргались.
_SHAPE = (
    "     .-------.     ",
    "   .'         '.   ",
    "  /             \\  ",
    " |               | ",
    " |               | ",
    " |               | ",
    "  \\             /  ",
    "   '.         .'   ",
    "     '-------'     ",
)

# Внутренняя область каждой строки (начало, конец) — там рисуются континенты.
_SPANS = (
    (0, 0),
    (6, 13),
    (4, 15),
    (3, 16),
    (3, 16),
    (3, 16),
    (4, 15),
    (6, 13),
    (0, 0),
)

# Текстура суши. Строки разной длины, сдвиг идёт по модулю длины — шва не видно.
_LAND = (
    "###   ##    ####    ##   ",
    " ##  ####  ##   ###  ##  ",
    "###    ##    ####   ###  ",
    "  ##  ###  ##    ###  ## ",
    " ##   ###    ##  ####    ",
    "###  ##   ####    ##  ###",
    "  #  ###   ##   ###  ##  ",
    " ##    ##  ###   ##  ### ",
    "###  ##    ##  ###   ##  ",
)

# Скорость по широте: у экватора быстрее, у полюсов медленнее — как у глобуса.
_SPEED = (0.25, 0.45, 0.65, 0.85, 1.0, 0.85, 0.65, 0.45, 0.25)

FRAME_COUNT = 18
FRAME_INTERVAL = 0.07


def _frame(index: int) -> str:
    rows: list[str] = []
    for row_index, shape in enumerate(_SHAPE):
        row = list(shape)
        start, end = _SPANS[row_index]
        land = _LAND[row_index]
        shift = round(index * _SPEED[row_index])
        for col in range(start, end):
            row[col] = land[(col - start + shift) % len(land)]
        rows.append("".join(row))
    return "\n".join(rows)


EARTH_FRAMES: tuple[str, ...] = tuple(_frame(i) for i in range(FRAME_COUNT))


class EarthSpinner(Static):
    """Планета, которая крутится, пока модель думает."""

    def __init__(self) -> None:
        super().__init__(EARTH_FRAMES[0], classes="earth")
        self._frame = 0
        self._timer = None
        self.display = False

    def start(self) -> None:
        self.display = True
        if self._timer is None:
            self._timer = self.set_interval(FRAME_INTERVAL, self._tick)

    def _tick(self) -> None:
        self._frame = (self._frame + 1) % len(EARTH_FRAMES)
        self.update(EARTH_FRAMES[self._frame])

    def stop(self) -> None:
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        self.display = False
