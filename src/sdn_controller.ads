-- SDN_Controller — Ada/SPARK rozhraní pro dvouvrstvou síť
-- Horní vrstva posílá příkazy spodní vrstvě přes TCP socket
--
-- Architektura:
--   Mincovna (Ada) → SDN Bridge (Python) → Faucet (OpenFlow)
--
-- Autor: Pan Jeskyně
-- Asistent: Kiro (Claude)
-- "Faucet ve vakuu" — izolovaná síť pod formální kontrolou

with Ada.Strings.Unbounded; use Ada.Strings.Unbounded;

package SDN_Controller is

   -- Typy příkazů pro spodní vrstvu (Faucet SDN)
   type Command_Type is
     (Block_Port,      -- Zablokovat síťový port
      Allow_Port,      -- Povolit síťový port
      Set_VLAN,        -- Nastavit VLAN přiřazení
      Add_ACL,         -- Přidat ACL pravidlo
      Remove_ACL,      -- Odebrat ACL pravidlo
      Get_Status,      -- Dotaz na stav sítě
      Reload_Config);  -- Reload Faucet konfigurace

   -- Stav připojení k SDN Bridge
   type Connection_State is (Disconnected, Connected, Error);

   -- Výsledek příkazu
   type Command_Result is record
      Success : Boolean := False;
      Message : Unbounded_String := Null_Unbounded_String;
   end record;

   -- Port SDN Bridge (TCP socket)
   Bridge_Port : constant := 4423;

   -- Připojit se k SDN Bridge
   procedure Connect
     with Post => Get_State = Connected or Get_State = Error;

   -- Odpojit se
   procedure Disconnect
     with Post => Get_State = Disconnected;

   -- Získat stav připojení
   function Get_State return Connection_State;

   -- ================================================================
   -- PŘÍKAZY PRO SÍŤOVOU VRSTVU
   -- ================================================================

   -- Zablokovat port (bezpečnostní izolace)
   function Block_Network_Port
     (Port_Number : Positive;
      Datapath    : String := "mincovna-switch")
      return Command_Result;

   -- Povolit port
   function Allow_Network_Port
     (Port_Number : Positive;
      Datapath    : String := "mincovna-switch")
      return Command_Result;

   -- Nastavit VLAN pro port
   function Set_Port_VLAN
     (Port_Number : Positive;
      VLAN_ID     : Positive)
      return Command_Result;

   -- Přidat ACL pravidlo
   function Add_ACL_Rule
     (ACL_Name : String;
      Rule     : String)  -- JSON formát pravidla
      return Command_Result;

   -- Získat stav celé sítě
   function Get_Network_Status return Command_Result;

   -- Reload konfigurace Faucet
   function Reload_Faucet return Command_Result;

end SDN_Controller;
