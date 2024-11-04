
## Useful command sequences

make clean
make

make clean
SIM=verilator make

cp tt_submission.zip!tt_um_dlmiles_tt05_i2c_bert.v tt_um_dlmiles_tt05_i2c_bert.v
ln -s tt_um_dlmiles_tt05_i2c_bert.v gate_level_netlist.v
make clean
GL_TEST=true make GATES=yes

### Verilator does not support UDP primitive keyword to allow gatelevel testing to take place

make clean
make TOPLEVEL=tb_maj3 MODULE=test_maj3

make clean
make TOPLEVEL=tb_maj5 MODULE=test_maj5

