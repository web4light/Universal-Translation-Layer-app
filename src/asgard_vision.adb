-- ============================================================
--  Asgard Vision — Implementation
--  "Oči pro ty co nevidí."
-- ============================================================

pragma SPARK_Mode (On);

package body Asgard_Vision is

   procedure Add_Component (S     : in out Scene;
                            State : Component_State;
                            OK    : out Boolean) is
   begin
      S.Comp_Count := S.Comp_Count + 1;
      S.Components (S.Comp_Count).State := State;
      OK := True;
   end Add_Component;

   procedure Add_Connection (S        : in out Scene;
                             From_Idx : Component_Count;
                             To_Idx   : Component_Count;
                             Hot      : Boolean;
                             OK       : out Boolean) is
   begin
      S.Conn_Count := S.Conn_Count + 1;
      S.Connections (S.Conn_Count).From_Idx := From_Idx;
      S.Connections (S.Conn_Count).To_Idx := To_Idx;
      S.Connections (S.Conn_Count).Hot_Path := Hot;
      OK := True;
   end Add_Connection;

   function Is_Valid (S : Scene) return Boolean is
   begin
      return S.Comp_Count > 0;
   end Is_Valid;

   function Count_On (S : Scene) return Component_Count is
      Count : Component_Count := 0;
   begin
      for I in 1 .. S.Comp_Count loop
         if S.Components (I).State = On then
            if Count < Max_Components then
               Count := Count + 1;
            end if;
         end if;
      end loop;
      return Count;
   end Count_On;

   function Count_Off (S : Scene) return Component_Count is
      Count : Component_Count := 0;
   begin
      for I in 1 .. S.Comp_Count loop
         if S.Components (I).State = Off then
            if Count < Max_Components then
               Count := Count + 1;
            end if;
         end if;
      end loop;
      return Count;
   end Count_Off;

   function All_On (S : Scene) return Boolean is
   begin
      for I in 1 .. S.Comp_Count loop
         if S.Components (I).State = Off then
            return False;
         end if;
      end loop;
      return True;
   end All_On;

end Asgard_Vision;
