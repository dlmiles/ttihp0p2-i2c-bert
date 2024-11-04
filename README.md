![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg) ![](../../workflows/test/badge.svg) ![](../../workflows/fpga/badge.svg)

# IHP0p2 I2C Bit Error Rate Tester (BERT)<br/>Echo ALU Peripheral

> [!IMPORTANT]
> My upstream project link maybe a better source of more up to date documentation. \
> [See also original upstream project](https://github.com/dlmiles/tt05-i2c-bert)

This project contains an updated version since
[TT05 I2C Bert project link](https://github.com/dlmiles/tt05-i2c-bert).

This IHP130 includes (partial advancement since TT05 but full features due TT09):
* The SCL pin is still on the old mapping. SCL=uio[2] which does not conform
with RP2040.  It is possible to bridge with uio[4] maybe via a 10k resistor,
or if you have full control to remove pull-up/pull-down and disable pin a
wire can be used to bridge pins.
* The SDA OE half-cycle glitch between ACKNACK and SEND is removed it is
thought to cause potential to disrupt SDA line state while SCL is high.
* Due to IHP130 not having 'Majority Voter 3-input' cell like SKY130 this is
implemented as module with discrete logic cells.
* The 'Majority Voter 5-input' was replaced with a proper implementation.
* STRETCH was improved, but not fully working (as in data load/store after
stretch is not expected to work, but the SCL state maybe seen).
* ui[7] now allows MUX of uo[7:0] between 7seg register and accumulator
register.
* Configuration latches refactored into latch_config.v to help cleanup code,
management of feature (so easier to be optional), support different technologies,
including FPGA.
* Configuration latches now have 4 delay-gate stages on pairs of bits with
the ENA rise trigger.

Non features (specific to IHP130 that warrant further understanding):
* i2c_bert.powerOnSense_GATE does not seem to fire (soon after RST_N
release) during gatelevel testing, this needs further review to better
understand.  So the relevant assert in the testbench is disabled search
IHP130_DISABLED_TEST for those locations.
* i2c_bert.powerOnSenseCaptured.GATE does fire so that item can be seen
working.
* cocotb testbench excludes for IHP130 needs further research.
* config.json probably did not support SYNTH_DEFINES ["TECH_IHP130"] this
affects delay-gate change listed above.

Features that did not make IHP0p2 but should be in TT09:
* Moving SCL pin from uio[2] to uio[4].  This project uses SDA=uio[3] and SCL=uio[2].
* STRETCH_rd (not fully tested, data read after STRETCH not working)
* STRETCH_wr (not fully tested, data write after STRETCH not working)
* SETLEDAC (set 7seg LED with current accumulator register)

While I made progress with building it on FPGA targetting Xilinx Arty-A7
(see other repository for code changes) to validate against a real RP2040
I2C hardware controller, this work is not complete.
So maybe this is I2C like but does not yet conform to specification.

# Tiny Tapeout Verilog Project Template

- [Read the documentation for project](docs/info.md)

## What is Tiny Tapeout?

Tiny Tapeout is an educational project that aims to make it easier and cheaper than ever to get your digital and analog designs manufactured on a real chip.

To learn more and get started, visit https://tinytapeout.com.

## Set up your Verilog project

1. Add your Verilog files to the `src` folder.
2. Edit the [info.yaml](info.yaml) and update information about your project, paying special attention to the `source_files` and `top_module` properties. If you are upgrading an existing Tiny Tapeout project, check out our [online info.yaml migration tool](https://tinytapeout.github.io/tt-yaml-upgrade-tool/).
3. Edit [docs/info.md](docs/info.md) and add a description of your project.
4. Adapt the testbench to your design. See [test/README.md](test/README.md) for more information.

The GitHub action will automatically build the ASIC files using [OpenLane](https://www.zerotoasiccourse.com/terminology/openlane/).

## Enable GitHub actions to build the results page

- [Enabling GitHub Pages](https://tinytapeout.com/faq/#my-github-action-is-failing-on-the-pages-part)

## Resources

- [FAQ](https://tinytapeout.com/faq/)
- [Digital design lessons](https://tinytapeout.com/digital_design/)
- [Learn how semiconductors work](https://tinytapeout.com/siliwiz/)
- [Join the community](https://tinytapeout.com/discord)
- [Build your design locally](https://www.tinytapeout.com/guides/local-hardening/)

## What next?

- [Submit your design to the next shuttle](https://app.tinytapeout.com/).
- Edit [this README](README.md) and explain your design, how it works, and how to test it.
- Share your project on your social network of choice:
  - LinkedIn [#tinytapeout](https://www.linkedin.com/search/results/content/?keywords=%23tinytapeout) [@TinyTapeout](https://www.linkedin.com/company/100708654/)
  - Mastodon [#tinytapeout](https://chaos.social/tags/tinytapeout) [@matthewvenn](https://chaos.social/@matthewvenn)
  - X (formerly Twitter) [#tinytapeout](https://twitter.com/hashtag/tinytapeout) [@tinytapeout](https://twitter.com/tinytapeout)
