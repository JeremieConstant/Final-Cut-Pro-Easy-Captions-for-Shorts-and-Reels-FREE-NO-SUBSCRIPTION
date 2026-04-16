# style.json – Reference

All colors are specified as RGB strings: `"R G B"` with values from `0.0` to `1.0`.

---

## font_color
Text color as an RGBA string `"R G B A"`.  
Default: `"1.0 1.0 1.0 1.0"` (white, fully opaque)

## position_y
Vertical position of the text in pixels, relative to the center of the frame.  
`0` = centered, negative = shift down, positive = shift up.

## resolution
Output video dimensions in pixels. The script derives the FCP format name automatically.

| Field    | Type | Description          | Common values              |
|----------|------|----------------------|----------------------------|
| `width`  | int  | Frame width in px    | `1080` (portrait), `1920` (landscape) |
| `height` | int  | Frame height in px   | `1920` (portrait), `1080` (landscape) |

**Examples:**

```json
"resolution": { "width": 1080, "height": 1920 }
```
→ Portrait / Vertical (Shorts, Reels, TikTok)

```json
"resolution": { "width": 1920, "height": 1080 }
```
→ Landscape / Widescreen (YouTube, standard video)

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
