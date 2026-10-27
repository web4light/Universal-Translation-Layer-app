pragma SPARK_Mode (On);

package body Flight_PID_Controller is

   type Wide_Val is delta 0.01 range -100000.0 .. 100000.0;
   for Wide_Val'Small use 0.01;

   Dt_Factor : constant Wide_Val := 0.05;

   function Saturate_Output (Val : Wide_Val) return Output_Val is
   begin
      if Val > 100.0 then
         return 100.0;
      elsif Val < -100.0 then
         return -100.0;
      else
         return Output_Val (Val);
      end if;
   end Saturate_Output;

   function Saturate_Accum (Val : Wide_Val) return Accum_Val is
   begin
      if Val > 100.0 then
         return 100.0;
      elsif Val < -100.0 then
         return -100.0;
      else
         return Accum_Val (Val);
      end if;
   end Saturate_Accum;

   procedure Initialize (
      State : out Controller_State;
      Kp    : in  Gain_Val;
      Ki    : in  Gain_Val;
      Kd    : in  Gain_Val
   ) is
   begin
      State.Kp         := Kp;
      State.Ki         := Ki;
      State.Kd         := Kd;
      State.Integrator := 0.0;
      State.Prev_Error := 0.0;
      State.Is_Active  := True;
   end Initialize;

   procedure Update_Control (
      State       : in out Controller_State;
      Setpoint    : in     Signal_Val;
      Measurement : in     Signal_Val;
      Actuator    : out    Output_Val
   ) is
      Err           : constant Error_Val := Error_Val (Setpoint) - Error_Val (Measurement);
      Diff          : constant Wide_Val  := Wide_Val (Err) - Wide_Val (State.Prev_Error);
      
      P_Term        : Wide_Val;
      I_Term        : Wide_Val;
      D_Term        : Wide_Val;
      Next_Accum    : Wide_Val;
      Total_Command : Wide_Val;
   begin
      -- Proporcionální složka
      P_Term := Wide_Val (Wide_Val (State.Kp) * Wide_Val (Err));

      -- Integrační složka s Anti-Windup saturací
      Next_Accum := Wide_Val (State.Integrator) + Wide_Val (Wide_Val (Err) * Dt_Factor);
      State.Integrator := Saturate_Accum (Next_Accum);
      I_Term := Wide_Val (Wide_Val (State.Ki) * Wide_Val (State.Integrator));

      -- Derivační složka
      D_Term := Wide_Val (Wide_Val (State.Kd) * Diff);

      -- Celkový výstup regulátoru s limitací na rozsah akčního členu
      Total_Command := P_Term + I_Term + D_Term;
      Actuator := Saturate_Output (Total_Command);

      -- Uložení historie chyby
      State.Prev_Error := Err;
   end Update_Control;

   procedure Reset_Integrator (State : in out Controller_State) is
   begin
      State.Integrator := 0.0;
   end Reset_Integrator;

end Flight_PID_Controller;
