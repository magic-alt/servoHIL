"""Independent electrical oracle: monitor/ARM/disarm and fail-low power status."""

def check(nets,values):
    def need(ref,pin,net):
        actual=nets.get(f'{ref}.{pin}')
        if actual!=net:raise ValueError(f'{ref}.{pin}: expected {net}, got {actual}')
    for i,mr in [(401,'ANALOG_OK'),(402,'INPUT_OK'),(403,'INPUT_OK')]:
        for pin,net in {6:'3V3_AON',5:f'SENSE_{i}',3:mr,2:'GND',1:'RAILS_OK'}.items():need(f'U{i}',pin,net)
        if not nets.get(f'U{i}.4','unconnected-').startswith('unconnected-'):raise ValueError('CT must be open for 20ms default')
    for pin,net in {1:'NEG_REF625',3:'NEG_FOLD',2:'GND',5:'3V3_AON',4:'NEG_VALID'}.items():need('U404',pin,net)
    for ref,pin,net in [('R540',1,'VREF_2V5'),('R540',2,'NEG_FOLD'),('R541',1,'-5V2_PVSS'),('R541',2,'NEG_FOLD'),('R542',1,'VREF_2V5'),('R542',2,'NEG_REF625'),('R543',1,'NEG_REF625'),('R543',2,'GND'),('D401',1,'NEG_FOLD'),('D401',2,'GND')]:need(ref,pin,net)
    for ref,pins in {'U405':{1:'PG_5V0',3:'PG_PVDD',6:'PG_PVSS',2:'GND',5:'3V3_AON',4:'ANALOG_PG'},'U406':{1:'ANALOG_PG',3:'NEG_VALID',6:'INPUT_OK',2:'GND',5:'3V3_AON',4:'ANALOG_OK'},'U407':{1:'HIL_ARM',2:'3V3_AON',6:'RAILS_OK',7:'3V3_AON',4:'GND',8:'3V3_AON',5:'ARM_LATCH'},'U408':{1:'RAILS_OK',3:'ARM_LATCH',6:'HIL_ARM',2:'GND',5:'1V8_D',4:'DAC_RESET_N'},'Q401':{1:'FAULT_BASE',2:'GND',3:'HIL_FAULT_N'},'Q402':{1:'RELEASE_BASE',2:'GND',3:'FAULT_BASE'}}.items():
        for pin,net in pins.items():need(ref,pin,net)
    for ref,a,b in [('R551','DAC_RESET_N','GND'),('R552','HIL_ARM','HIL_FAULT_N'),('R553','HIL_ARM','FAULT_BASE'),('R554','FAULT_BASE','GND'),('R555','ARM_LATCH','RELEASE_BASE'),('R556','RELEASE_BASE','GND')]:
        need(ref,1,a);need(ref,2,b)
    if 'U409' in values:raise ValueError('unbiased old fault buffer must not remain')
    if not values.get('R551','').startswith('10k'):raise ValueError('reset default pulldown missing')
    print('Power qualification / re-arm / disarm / host-referenced fault pin oracle PASS')
