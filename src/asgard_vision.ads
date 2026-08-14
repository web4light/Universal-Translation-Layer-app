-- ============================================================
--  Asgard Vision — Oči pro slepé AI agenty
--
--  MCP server co dává zrak jakémukoliv agentovi.
--  Čte obrázky, videa, generuje SVG schémata.
--
--  SPARK proved — bounded buffers, žádný overflow.
--  Žádná Java. Čistá Ada.
--
--  Autor: Pan Jeskyně
--  Licence: Apache 2.0
-- ============================================================

pragma SPARK_Mode (On);

package Asgard_Vision is

   -- Limity
   Max_Components   : constant := 50;
   Max_Connections  : constant := 100;
   Max_Name_Length  : constant := 64;
   Max_Value_Length : constant := 128;

   subtype Component_Count is Natural range 0 .. Max_Components;
   subtype Connection_Count is Natural range 0 .. Max_Connections;
   subtype Name_Length is Natural range 0 .. Max_Name_Length;
   subtype Value_Length is Natural range 0 .. Max_Value_Length;

   -- Stav komponenty (jistič)
   type Component_State is (On, Off);

   -- Jedna komponenta v SCADA diagramu
   type Component is record
      Name_Len  : Name_Length := 0;
      Port_Len  : Name_Length := 0;
      Value_Len : Value_Length := 0;
      State     : Component_State := On;
      X         : Natural range 0 .. 2000 := 0;
      Y         : Natural range 0 .. 2000 := 0;
   end record;

   -- Jedno spojení
   type Connection is record
      From_Idx : Component_Count := 0;
      To_Idx   : Component_Count := 0;
      Hot_Path : Boolean := False;
   end record;

   -- Pole komponent a spojení
   type Component_Array is array (1 .. Max_Components) of Component;
   type Connection_Array is array (1 .. Max_Connections) of Connection;

   -- Celá scéna
   type Scene is record
      Components : Component_Array;
      Comp_Count : Component_Count := 0;
      Connections : Connection_Array;
      Conn_Count : Connection_Count := 0;
   end record;

   -- =========================================================
   --  Operace
   -- =========================================================

   -- Přidej komponentu do scény
   procedure Add_Component (S     : in out Scene;
                            State : Component_State;
                            OK    : out Boolean)
     with Pre  => S.Comp_Count < Max_Components,
          Post => (if OK then S.Comp_Count = S.Comp_Count'Old + 1
                   else S.Comp_Count = S.Comp_Count'Old);

   -- Přidej spojení
   procedure Add_Connection (S        : in out Scene;
                             From_Idx : Component_Count;
                             To_Idx   : Component_Count;
                             Hot      : Boolean;
                             OK       : out Boolean)
     with Pre  => S.Conn_Count < Max_Connections
                  and From_Idx >= 1 and From_Idx <= S.Comp_Count
                  and To_Idx >= 1 and To_Idx <= S.Comp_Count,
          Post => (if OK then S.Conn_Count = S.Conn_Count'Old + 1
                   else S.Conn_Count = S.Conn_Count'Old);

   -- Validuj scénu
   function Is_Valid (S : Scene) return Boolean
     with Post => Is_Valid'Result = (S.Comp_Count > 0);

   -- Počet ON komponent
   function Count_On (S : Scene) return Component_Count;

   -- Počet OFF komponent
   function Count_Off (S : Scene) return Component_Count;

   -- Všechny ON?
   function All_On (S : Scene) return Boolean;

end Asgard_Vision;
