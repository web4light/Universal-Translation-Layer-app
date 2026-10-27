pragma SPARK_Mode (On);

package Flight_PID_Controller is

   -- Pevná řádová čárka pro deterministické letecké výpočty (DO-178C DAL-A)
   type Signal_Val is delta 0.01 range -500.0 .. 500.0;
   for Signal_Val'Small use 0.01;

   type Error_Val  is delta 0.01 range -1000.0 .. 1000.0;
   for Error_Val'Small use 0.01;

   type Gain_Val   is delta 0.01 range 0.0 .. 10.0;
   for Gain_Val'Small use 0.01;

   type Output_Val is delta 0.01 range -100.0 .. 100.0;
   for Output_Val'Small use 0.01;

   type Accum_Val  is delta 0.01 range -100.0 .. 100.0;
   for Accum_Val'Small use 0.01;

   -- PID regulátor bez dynamické alokace paměti
   type Controller_State is record
      Kp         : Gain_Val;
      Ki         : Gain_Val;
      Kd         : Gain_Val;
      Integrator : Accum_Val;
      Prev_Error : Error_Val;
      Is_Active  : Boolean;
   end record;

   -- Inicializace regulátoru
   procedure Initialize (
      State : out Controller_State;
      Kp    : in  Gain_Val;
      Ki    : in  Gain_Val;
      Kd    : in  Gain_Val
   )
   with
      Global  => null,
      Depends => (State => (Kp, Ki, Kd)),
      Post    => State.Kp = Kp and then
                 State.Ki = Ki and then
                 State.Kd = Kd and then
                 State.Integrator = 0.0 and then
                 State.Prev_Error = 0.0 and then
                 State.Is_Active;

   -- Výpočet kroku regulace s anti-windup saturací a derivačním filtrem
   procedure Update_Control (
      State       : in out Controller_State;
      Setpoint    : in     Signal_Val;
      Measurement : in     Signal_Val;
      Actuator    : out    Output_Val
   )
   with
      Global  => null,
      Depends => (
         State    =>+ (Setpoint, Measurement),
         Actuator =>  (State, Setpoint, Measurement)
      ),
      Pre     => State.Is_Active,
      Post    => Actuator in -100.0 .. 100.0 and then
                 State.Is_Active;

   -- Bezpečný reset integrační složky
   procedure Reset_Integrator (State : in out Controller_State)
   with
      Global  => null,
      Depends => (State =>+ null),
      Pre     => State.Is_Active,
      Post    => State.Integrator = 0.0 and then
                 State.Is_Active;

end Flight_PID_Controller;
