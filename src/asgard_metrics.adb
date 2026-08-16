-- ============================================================
--  Asgard Metrics — Implementation
-- ============================================================

pragma SPARK_Mode (On);

package body Asgard_Metrics is

   procedure Initialize (State : out Asgard_State) is
   begin
      State := (Pipeline => (others => <>),
                System   => (others => <>),
                Security => (others => <>));
   end Initialize;

   procedure Record_Translation (State   : in out Asgard_State;
                                 Success : Boolean) is
   begin
      State.Pipeline.Translations_Total :=
        State.Pipeline.Translations_Total + 1;

      if Success then
         if State.Pipeline.Translations_Success < Max_Counter then
            State.Pipeline.Translations_Success :=
              State.Pipeline.Translations_Success + 1;
         end if;
      else
         if State.Pipeline.Translations_Failed < Max_Counter then
            State.Pipeline.Translations_Failed :=
              State.Pipeline.Translations_Failed + 1;
         end if;
      end if;

      State.Pipeline.Success_Rate := Get_Success_Rate (State);
   end Record_Translation;

   procedure Record_Dubbing (State    : in out Asgard_State;
                             Segments : Counter_Value) is
   begin
      State.Pipeline.Dubbing_Segments :=
        State.Pipeline.Dubbing_Segments + Segments;
   end Record_Dubbing;

   procedure Record_Spark_Check (State  : in out Asgard_State;
                                 Proved : Boolean) is
   begin
      if Proved then
         State.System.Spark_Checks_Proved :=
           State.System.Spark_Checks_Proved + 1;
      else
         if State.System.Spark_Checks_Failed < Max_Counter then
            State.System.Spark_Checks_Failed :=
              State.System.Spark_Checks_Failed + 1;
         end if;
      end if;
   end Record_Spark_Check;

   procedure Record_Auth (State   : in out Asgard_State;
                          Success : Boolean) is
   begin
      if Success then
         State.Security.Auth_Success :=
           State.Security.Auth_Success + 1;
      else
         if State.Security.Auth_Failed < Max_Counter then
            State.Security.Auth_Failed :=
              State.Security.Auth_Failed + 1;
         end if;
      end if;
   end Record_Auth;

   function Get_Success_Rate (State : Asgard_State) return Percent is
      Total : constant Counter_Value := State.Pipeline.Translations_Total;
      Good  : constant Counter_Value := State.Pipeline.Translations_Success;
   begin
      if Total = 0 or Good = 0 then
         return 0;
      end if;

      if Good >= Total then
         return 100;
      end if;

      -- Good < Total, tak Good/Total < 1.0, výsledek < 100
      return Percent (Good / (Total / 100 + 1));
   end Get_Success_Rate;

end Asgard_Metrics;
