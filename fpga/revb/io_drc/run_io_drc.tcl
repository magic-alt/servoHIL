# Rev.B AXU2CGB package-pin / IOSTANDARD DRC harness.
# Usage:
#   vivado -mode batch -source fpga/revb/io_drc/run_io_drc.tcl \
#     -tclargs build/revb-vivado-io-drc <source_commit>
#
# This run does NOT perform or claim functional STA.

set script_dir [file dirname [file normalize [info script]]]
set repo_root [file normalize [file join $script_dir ../../..]]
set out_dir [expr {$argc >= 1 ? [lindex $argv 0] : [file join $repo_root build/revb-vivado-io-drc]}]
set source_commit [expr {$argc >= 2 ? [lindex $argv 1] : "UNBOUND"}]
set part "xczu2cg-sfvc784-1-e"
set top "servohil_io_drc_top"
set rtl [file join $script_dir servohil_io_drc_top.sv]
set xdc [file join $script_dir axu2cgb_io_drc.xdc]

file mkdir $out_dir
create_project -in_memory -part $part revb_io_drc
read_verilog -sv $rtl
read_xdc $xdc

synth_design -top $top -part $part -flatten_hierarchy none
opt_design
place_design

report_drc -file [file join $out_dir report_drc.rpt]
report_io -file [file join $out_dir report_io.rpt]
report_utilization -file [file join $out_dir report_utilization.rpt]
write_checkpoint -force [file join $out_dir io_drc_placed.dcp]

set fh [open [file join $out_dir run_identity.txt] w]
puts $fh "purpose=REV_B_IO_DRC_HARNESS_ONLY"
puts $fh "vivado_version=[version -short]"
puts $fh "target_part=$part"
puts $fh "top_module=$top"
puts $fh "rtl=$rtl"
puts $fh "xdc=$xdc"
puts $fh "source_commit=$source_commit"
puts $fh "timing_claim=NOT_RUN"
close $fh

set bad 0
foreach violation [get_drc_violations -quiet] {
    set severity [get_property SEVERITY $violation]
    if {$severity eq "Error" || $severity eq "Critical Warning"} {
        puts stderr "FAIL DRC: [get_property RULEDECK $violation] / [get_property CHECK $violation] / $severity"
        incr bad
    }
}
if {$bad != 0} {
    puts stderr "Rev.B IO DRC harness FAILED with $bad Error/Critical Warning violation(s)."
    exit 2
}
puts "Rev.B IO DRC harness PASS for package-pin/IOSTANDARD scope only; timing remains NOT_RUN."
exit 0
