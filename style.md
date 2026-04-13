# style.json – Reference

All colors are specified as RGB strings: `"R G B"` with values from `0.0` to `1.0`.

---

## font_color
Text color as an RGBA string `"R G B A"`.  
Default: `"1.0 1.0 1.0 1.0"` (white, fully opaque)

## position_y
Vertical position of the text in pixels, relative to the center of the frame.  
`0` = centered, negative = shift down, positive = shift up.

---

## stroke

| Field     | Type   | Description                                  |
|-----------|--------|----------------------------------------------|
| `enabled` | bool   | Enable stroke (`true` / `false`)             |
| `color`   | string | Color as `"R G B"`                           |
| `opacity` | float  | Opacity `0.0`–`1.0` (0 % – 100 %)           |
| `width`   | int    | Stroke width in points                       |

---

## shadow

| Field      | Type   | Description                                  |
|------------|--------|----------------------------------------------|
| `enabled`  | bool   | Enable shadow (`true` / `false`)             |
| `color`    | string | Color as `"R G B"`                           |
| `opacity`  | float  | Opacity `0.0`–`1.0` (0 % – 100 %)           |
| `distance` | int    | Shadow distance in points                    |
| `angle`    | int    | Angle in degrees (`315` = upper left)        |
