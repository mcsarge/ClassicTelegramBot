import logging

log = logging.getLogger('classic_telegram_bot')

chargeStates =    {
    0: 'Resting',
    3: 'Absorb',
    4: 'Bulk MPPT',
    5: 'Float',
    6: 'Float MPPT',
    7: 'Equalize',
   10: 'Hyper VOC',
   18: 'Eq MPPT'}

reasonForResting = {
    1:'Anti-Click. Not enough power available (Wake Up)',
    2:'Insane Ibatt Measurement (Wake Up)',
    3:'Negative Current (load on PV input ?) (Wake Up)',
    4:'PV Input Voltage lower than Battery V (Vreg state)',
    5:'Too low of power out and Vbatt below set point for > 90 seconds',
    6:'FET temperature too high (Cover is on maybe ?)',
    7:'Ground Fault Detected',
    8:'Arc Fault Detected',
    9:'Too much negative current while operating (backfeed from battery out of PV input)',
   10:'Battery is less than 8.0 Volts',
   11:'PV input is available but V is rising too slowly. Low Light or bad connection (Solar mode)',
   12:'Voc has gone down from last Voc or low light. Re-check (Solar mode)',
   13:'Voc has gone up from last Voc enough to be suspicious. Re-check (Solar mode)',
   14:'PV input is available but V is rising too slowly. Low Light or bad connection (Solar mode)',
   15:'Voc has gone down from last Voc or low light. Re-check (Solar mode)',
   16:'Mppt MODE is OFF (Usually because user turned it off)',
   17:'PV input is higher than operation range (too high for 150V Classic)',
   18:'PV input is higher than operation range (too high for 200V Classic)',
   19:'PV input is higher than operation range (too high for 250V or 250KS)',
   22:'Average Battery Voltage is too high above set point',
   25:'Battery Voltage too high of Overshoot (small battery or bad cable ?)',
   26:'Mode changed while running OR Vabsorb raised more than 10.0 Volts at once OR Nominal Vbatt changed by modbus command AND MpptMode was ON when changed',
   27:'bridge center == 1023 (R132 might have been stuffed) This turns MPPT Mode to OFF',
   28:'NOT Resting but RELAY is not engaged for some reason',
   29:'ON/OFF stays off because WIND GRAPH is illegal (current step is set for > 100 amps)',
   30:'PkAmpsOverLimit… Software detected too high of PEAK output current',
   31:'AD1CH.IbattMinus > 900 Peak negative battery current > 90.0 amps (Classic 250)',
   32:'Aux 2 input commanded Classic off. for HI or LO (Aux2Function == 15 or 16)',
   33:'OCP in a mode other than Solar or PV-Uset',
   34:'AD1CH.IbattMinus > 900 Peak negative battery current > 90.0 amps (Classic 150, 200)',
   35:'Battery voltage is less than Low Battery Disconnect (LBD) Typically Vbatt is less than 8.5 volts'}

batteryChargeState = {
    0: {'Resting', 'Off , No Power, Waiting for Power Source, Battery V over set point, etc.'},
    3: {'Absorb', 'Regulating battery voltage at Equalize Set point'},
    4: {'BulkMppt', 'Max Power Point Tracking until Absorb (Bulk Terminate) Voltage reached'},
    5: {'Float', 'Battery is FULL and regulating battery voltage at Float Set point'},
    6: {'FloatMppt', 'Max Power Point Tracking. Seeking Float set point Voltage'},
    7: {'Equalize', 'Regulating battery voltage at Equalize Set point'},
   10: {'HyperVoc', 'Input Voltage is above maximum Classic operating Voltage'},
   18: {'EqMppt', 'Max Power Point Tracking. Seeking Equalize set point Voltage'}
}