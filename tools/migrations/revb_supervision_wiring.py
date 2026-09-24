"""Local wiring of power qualification/status; no new safety capability is claimed."""
from revb_wiring import Editor


def status(directory):
    d=Editor(directory,'41_power_status','POWER STATUS - host-referenced default fault and qualified release')
    for ref,x,y,a in [('Q401',70,35,0),('Q402',30,55,0),('R552',110,28,270),
                      ('R553',52,28,270),('R554',53,44,270),('R555',14,54,0),('R556',18,64,270)]:d.place(ref,x,y,a)
    d.anchor('TP402',1,118,34)
    d.bus('HIL_ARM',20,['R552.1','R553.1'],8,110)
    d.wire('HIL_FAULT_N','Q401.3',(110,34),'TP402.1')
    d.wire('HIL_FAULT_N','R552.2',(110,34));d.label('HIL_FAULT_N',(118,34))
    d.wire('FAULT_BASE','R553.2',(52,34),(53,34),'Q401.1')
    d.wire('FAULT_BASE',(53,34),'R554.1')
    d.wire('FAULT_BASE','Q402.3',(53,54),(53,34));d.label('FAULT_BASE',(53,37))
    d.wire('RELEASE_BASE','R555.2','Q402.1')
    d.wire('RELEASE_BASE',(18,54),'R556.1');d.label('RELEASE_BASE',(18,58))
    d.terminal('R555',1,-4)
    for r,pin in [('R554',2),('R556',2),('Q401',2),('Q402',2)]:d.gnd(r,pin,4)
    d.note('HOST HIL_ARM supplies both the status pull-up and default-fault bias. Expansion supply never directly pulls the status high.',8,80,1.1)
    d.note('ARM_LATCH drives Q402: only qualified, armed power releases Q401. HIL_FAULT_N LOW also means disarmed.',8,87,1.1)
    d.note('This is power status, not a full watchdog or certified safety function. Partial-power/transient behavior still requires bench tests.',8,94,1.1)
    d.finish()


def supervision(directory):
    d=Editor(directory,'40_power_supervision','POWER QUALIFICATION - rail monitors, negative sense, deliberate re-arm and reset driver')
    for i,off,rail in [(401,0,'1V8_D'),(402,70,'3V3_D'),(403,140,'VREF_2V5')]:
        base=500+(i-401)*10;u=f'U{i}'
        def p(x,y):return x+off,y
        d.note(rail+' rail supervision',off+8,15,1.5)
        for ref,x,y,a in [(u,35,30,0),(f'R{base}',15,25,270),(f'R{base+1}',15,38,270),
                          (f'C{base}',22,38,270),(f'C{base+1}',50,34,270)]:d.place(ref,x+off,y,a)
        d.terminal(f'R{base}',1,-3)
        sense=f'SENSE_{i}'
        d.wire(sense,f'R{base}.2',p(15,32),f'R{base+1}.1')
        d.wire(sense,p(15,32),p(22,32),f'C{base}.1')
        d.wire(sense,u+'.5',p(24,29),p(24,32),p(22,32));d.label(sense,p(18,32))
        d.wire('3V3_AON',u+'.6',p(25,27),p(25,21),p(50,21),f'C{base+1}.1');d.label('3V3_AON',p(47,21))
        mr='ANALOG_OK' if i==401 else 'INPUT_OK'
        d.wire(mr,u+'.3',p(26,31),p(26,46),p(16,46))
        if i!=401:d.label(mr,p(16,46),'right')
        d.wire('RAILS_OK',u+'.1',p(60,27),p(60,55))
        for ref in (f'R{base+1}',f'C{base}',f'C{base+1}'):d.gnd(ref,2)
        d.gnd(u,2,9)
    d.place('R530',218,44,270);d.terminal('R530',1,-3)
    d.wire('RAILS_OK',(60,55),(218,55),'R530.2');d.label('RAILS_OK',(211,55))
    # Independent negative rail comparator and explicit clamp/hysteresis network.
    for ref,x,y,a in [('U404',46,103,0),('R542',20,88,270),('R543',20,100,270),
                      ('R540',10,116,270),('R541',26,116,270),('R544',46,85,0),('R545',86,100,270),
                      ('C540',42,132,270),('C541',78,110,270),('D401',50,132,270),
                      ('D402',57,129,270),('D403',27,88,270)]:d.place(ref,x,y,a)
    d.note('PVSS independent sense / hysteresis',8,72,1.5)
    d.terminal('R542',1,-3);d.terminal('R540',1,-3);d.terminal('R541',1,3)
    d.wire('NEG_REF625','R542.2',(20,94),'R543.1')
    d.wire('NEG_REF625',(20,94),(32,94),(32,101),'U404.1')
    d.wire('NEG_REF625','D403.2',(27,94))
    d.wire('NEG_REF625','R544.2',(48,94),(32,94));d.label('NEG_REF625',(29,94))
    d.terminal('D403',1,3)
    d.wire('NEG_FOLD','R540.2',(10,126),(63,126),(63,131),'D402.2')
    d.wire('NEG_FOLD','R541.2',(26,126))
    d.wire('NEG_FOLD','U404.3',(36,103),(36,126))
    d.wire('NEG_FOLD','C540.1',(42,126));d.wire('NEG_FOLD','D401.1',(50,126));d.label('NEG_FOLD',(36,123))
    d.terminal('D402',1,3)
    d.wire('3V3_AON','U404.5',(54,94),(86,94),'R545.1')
    d.wire('3V3_AON',(78,94),'C541.1');d.label('3V3_AON',(84,94))
    d.wire('NEG_VALID','U404.4',(60,103),(60,120),(88,120),(88,78),(44,78),'R544.1')
    d.wire('NEG_VALID','R545.2',(86,120));d.label('NEG_VALID',(83,120))
    for ref in ('R543','C540','C541','D401'):d.gnd(ref,2)
    d.gnd('U404',2)
    # PG/negative/input combine, then feed the monitor's manual-reset input.
    for ref,x,y,a in [('U405',126,90,0),('U406',191,90,0),('C550',146,100,270),('C551',211,100,270),
                      ('U407',126,140,0),('U408',191,140,0),('R550',100,145,270),('R551',219,151,270),
                      ('C552',142,150,270),('C553',211,150,270),('C554',152,150,270)]:d.place(ref,x,y,a)
    d.note('Supply qualification',109,75,1.5)
    for pin in (1,3,6):d.terminal('U405',pin,-4)
    d.wire('ANALOG_PG','U405.4',(165,89),(165,87),'U406.1');d.label('ANALOG_PG',(151,89))
    d.wire('NEG_VALID',(86,120),(165,120),(165,95),(179,95),(179,89),'U406.3')
    d.wire('INPUT_OK','U406.6',(181,91),(181,110),(193,110));d.label('INPUT_OK',(193,110))
    d.wire('ANALOG_OK','U406.4',(222,89),(222,63),(5,63),(5,46),(16,46));d.label('ANALOG_OK',(191,63))
    for u,c,x in [('U405','C550',146),('U406','C551',211)]:
        d.wire('3V3_AON',u+'.5',(x,87),c+'.1');d.label('3V3_AON',(x,87));d.gnd(c,2);d.gnd(u,2)
    d.note('Re-arm latch / immediate disarm',103,126,1.5)
    d.wire('HIL_ARM','U407.1',(100,136),'R550.1')
    d.wire('HIL_ARM',(100,136),(100,130),(174,130),(174,141),'U408.6');d.label('HIL_ARM',(102,130))
    for pin in (2,7):d.terminal('U407',pin,-3)
    d.terminal('U407',6,-3);d.terminal('U408',1,-3)
    d.wire('3V3_AON','U407.8',(142,136),'C552.1')
    d.wire('3V3_AON','C552.1','C554.1');d.label('3V3_AON',(142,136))
    d.wire('ARM_LATCH','U407.5',(159,138),(159,139),'U408.3');d.label('ARM_LATCH',(147,138))
    d.wire('1V8_D','U408.5',(211,137),'C553.1');d.label('1V8_D',(211,137))
    d.wire('DAC_RESET_N','U408.4',(221,139));d.wire('DAC_RESET_N',(219,139),'R551.1');d.label('DAC_RESET_N',(221,139))
    for ref in ('R550','R551','C552','C553','C554'):d.gnd(ref,2)
    d.gnd('U407',4);d.gnd('U408',2)
    d.anchor('TP401',1,225,152);d.terminal('TP401',1,-3)
    d.note('TP401 HIL_WDI is a reserved input, NOT a watchdog. Complete heartbeat, AO disconnect and DUT gate inhibit remain OPEN.',8,159,1.0)
    d.note('Power fault clears the latch; a fresh ARM edge is required. HIL_ARM LOW immediately holds DAC reset asserted. Hardware validation remains pending.',8,163,1.0)
    d.finish()
