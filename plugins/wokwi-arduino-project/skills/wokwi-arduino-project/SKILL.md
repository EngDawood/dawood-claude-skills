---
name: wokwi-arduino-project
description: "Use when the user asks to simulate an Arduino project in Wokwi (sketch.ino, diagram.json, libraries.txt). Also use when they ask for the Arduino code of a hardware project, how to wire the physical parts, or which components they need. Builds the simulation, the sketch and the wiring guide from one pin map so they always match. Triggers: simulate it in Wokwi, diagram.json, Arduino code for my mini project, how do I connect the hardware, physical components, lab project proposal with a hardware list."
---

# Arduino project: Wokwi simulation, sketch and hardware wiring

Build the simulation, the sketch and the wiring guide from one pin map so all three match. Reply in the user's language and keep it short. Give each file as its own fenced block named by file (sketch.ino, diagram.json, libraries.txt) so the user can paste it into the Wokwi tabs.

## 1. Confirm the physical parts

Ask once, in one message, only what the request does not say: the board (default Arduino Uno), the exact variant of each module, and the output wanted (LCD, Serial Monitor, units).

The 16x2 LCD comes in two kinds, and mixing them up costs a full redo:

- Plain: 16 pins marked VSS VDD V0 RS RW E D0 to D7 A K (some boards print BLA BLK). Needs a 10k potentiometer on V0.
- I2C backpack: 4 pins marked GND VCC SDA SCL.

If the user does not know, ask for a photo of the pin side. While waiting, simulate the plain type (the Wokwi default) and say so in one line. Why: this session simulated an I2C LCD first, then the real LCD was plain, so the sketch, the wiring and the slides had to be redone.

Done when every module has a confirmed variant, or a photo is requested and the plain assumption is stated.

## 2. Write the pin map

One table: part pin, Arduino pin, wire color. Include power and ground for every module. Reuse the same colors in diagram.json and in the hardware guide. If the user already has a wiring or a diagram, keep their pins.

| Part pin | Arduino pin | Wire |
|---|---|---|
| HC-SR04 TRIG | D9 | green |
| LCD E | D11 | purple |

Done when every signal appears once and every module has its power and ground rows.

## 3. Write sketch.ino

- Use the pins from the pin map. The same sketch runs in Wokwi and on the board, with no simulation-only code.
- Plain LCD: LiquidCrystal, constructor order RS, E, D4, D5, D6, D7.
- I2C LCD: LiquidCrystal_I2C at address 0x27, with lcd.init() and lcd.backlight().
- Print padded text over each LCD row instead of calling lcd.clear() inside loop(). It avoids flicker and leftover characters.
- Use exact Arduino capitalization (digitalWrite, delayMicroseconds).

Done when every pin number in the code matches the pin map and every Arduino function is spelled in its exact case.

## 4. Write diagram.json

Use exact Wokwi pin names. In this session an unknown name drew no wire and raised no visible error.

| Part | Valid pin names |
|---|---|
| wokwi-arduino-uno | 0 to 13, A0 to A5, 5V, GND.1 (top header, next to 13), GND.2, GND.3 |
| wokwi-lcd1602, plain (default) | VSS VDD V0 RS RW E D0 to D7 A K |
| wokwi-lcd1602 with attrs {"pins": "i2c"} | GND VCC SDA SCL |
| wokwi-hc-sr04 | VCC TRIG ECHO GND |
| wokwi-potentiometer | GND SIG VCC |

Rules:

- The LCD enable pin is E, not EN. The Uno has GND.1 to GND.3 only, so GND.4 and GND.5 do not exist. Several wires may end on one GND pin.
- V0 is not simulated. Wire it to GND, and leave the potentiometer out of the simulation unless the sketch reads it with analogRead.
- Connection format: [from, to, color, route], for example ["lcd:E", "uno:11", "purple", []].
- When the user pastes their own diagram.json, edit that text. Keep part ids, top and left values, colors and routes, and change only the connections asked for. Why: a regenerated file reset the user's layout and colors, and they had to ask again.

Why the names matter: a plain-LCD diagram in this session used lcd:EN, uno:GND.4 and uno:GND.5. None of them exists, so E, RW and K had no wire and the LCD stayed blank. That is the likely cause. The corrected diagram was not re-run before the user moved on to the I2C version, which worked.

Done when each row of the pin map has one connection using a name from the table, and the user confirms each wire visibly ends on a pin in the render.

## 5. Write libraries.txt

Only third-party libraries need a line, for example LiquidCrystal I2C for the I2C LCD. Wire, SPI and the other standard Arduino libraries are built in.

Done when libraries.txt lists exactly the third-party libraries the sketch includes, or the file is not mentioned.

## 6. Debug a blank LCD in this order

1. Zoom the render: do E, RW, VSS, VDD, A and K each have a wire ending on the pin?
2. Contrast: in Wokwi, V0 goes to GND. On hardware, turn the potentiometer slowly.
3. RS, E and D4 to D7 match the LiquidCrystal constructor order.
4. Backlight: A to 5V, K to GND.
5. Only then look at libraries.txt.

Do not switch to the I2C LCD to dodge a wiring fault, because the real part then no longer matches. Do not offer a contrast attribute, because the LCD part has none (its attributes are pins, i2cAddress, color, background and variant).

Done when the user's screenshot shows text, or steps 1 to 5 are ruled out.

## 7. Write the hardware guide

Give:

- A components table with quantities. Include the parts the simulator hides: breadboard, USB cable, jumper wires, and for a plain LCD a 10k potentiometer (the marking B10K means 10k).
- One table per module: module pin, Arduino pin. Count LCD pins from pin 1 (VSS) on the printed silkscreen.
- Potentiometer: left pin to GND, middle pin (wiper) to V0, right pin to 5V.
- Bring-up order: wire with the USB unplugged, check each wire end against the tables, upload, then turn the potentiometer slowly until text shows.

Tell the user to read the printed label beside each Arduino header hole. A wire on D13 instead of D11 was seen in this session, and the E pin stayed unwired.

Done when every wire has both ends in a table and the bring-up order is listed.

## 8. Upload errors seen

- redefinition of 'void setup()': two .ino files in the sketch folder. Keep one tab.
- 'digitalwrite' was not declared in this scope: write digitalWrite with a capital W.

Done when the user's compile output reports the sketch size.

## Delivery order

Pin map, sketch.ino, diagram.json (and libraries.txt if needed), then the hardware guide. End by asking for a Wokwi screenshot.

## After each run

When the task is done, check whether this run taught something this skill does not already
say: an error you hit, a correction from the user, or a better approach you found. If so,
propose at most 3 edits to this file, each as the current line, the new text, and a one-line
reason. Change nothing until the user approves, then apply only the approved edits:

- Claude Code: edit this `SKILL.md` directly.
- claude.ai: run `session-to-skill` to produce the updated skill for re-upload.

If there is no real lesson, say nothing.
