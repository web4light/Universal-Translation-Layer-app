-- ============================================================
--  Shadow Node — Implementace
--  Monitoring Primary Node na portu 9302
--  Automatický failover za 15 sekund
--  Prometheus HTTP server na portu 9303
-- ============================================================
pragma SPARK_Mode (Off);

with Ada.Text_IO;           use Ada.Text_IO;
with Ada.Calendar;          use Ada.Calendar;
with Ada.Calendar.Formatting;
with GNAT.Sockets;          use GNAT.Sockets;
with Ada.Streams;           use Ada.Streams;

package body Shadow_Node is

   -- Sdílený stav (chráněný objektem)
   protected Shared_State is
      procedure Set_Mode (M : Node_Mode);
      procedure Set_Primary_Alive (V : Boolean);
      procedure Inc_Sync_Errors;
      procedure Set_Coins (V : Natural);
      function Get_Mode return Node_Mode;
      function Get_Primary_Alive return Boolean;
      function Get_Sync_Errors return Natural;
      function Get_Coins return Natural;
   private
      Mode             : Node_Mode := Shadow;
      Primary_Alive    : Boolean   := True;
      Sync_Errors      : Natural   := 0;
      Coins            : Natural   := 0;
   end Shared_State;

   protected body Shared_State is
      procedure Set_Mode (M : Node_Mode) is
      begin Mode := M; end Set_Mode;
      procedure Set_Primary_Alive (V : Boolean) is
      begin Primary_Alive := V; end Set_Primary_Alive;
      procedure Inc_Sync_Errors is
      begin Sync_Errors := Sync_Errors + 1; end Inc_Sync_Errors;
      procedure Set_Coins (V : Natural) is
      begin Coins := V; end Set_Coins;
      function Get_Mode return Node_Mode is (Mode);
      function Get_Primary_Alive return Boolean is (Primary_Alive);
      function Get_Sync_Errors return Natural is (Sync_Errors);
      function Get_Coins return Natural is (Coins);
   end Shared_State;

   -- =========================================================
   --  Log helper
   -- =========================================================
   procedure Log (Prefix : String; Msg : String) is
      T : constant String := Ada.Calendar.Formatting.Image (Clock);
   begin
      Put_Line ("[" & T (12 .. 19) & "] [" & Prefix & "] " & Msg);
   end Log;

   -- =========================================================
   --  HTTP GET na localhost:9302/metrics
   -- =========================================================
   function Check_Primary_Health (State : in out Shadow_State) return Boolean is
      Sock  : Socket_Type;
      Addr  : Sock_Addr_Type;
      Req   : constant String :=
         "GET /metrics HTTP/1.0" & ASCII.CR & ASCII.LF &
         "Host: localhost" & ASCII.CR & ASCII.LF &
         ASCII.CR & ASCII.LF;
      Buf   : Stream_Element_Array (1 .. 64);
      Last  : Stream_Element_Offset;
   begin
      Create_Socket (Sock);
      Set_Socket_Option (Sock, Socket_Level, (Receive_Timeout, 2.0));
      Addr.Addr := Inet_Addr ("127.0.0.1");
      Addr.Port := Port_Type (Primary_Port);
      Connect_Socket (Sock, Addr);
      declare
         Chan : Stream_Access := Stream (Sock);
      begin
         String'Write (Chan, Req);
         Receive_Socket (Sock, Buf, Last);
      end;
      Close_Socket (Sock);
      State.Is_Primary_Alive := True;
      Shared_State.Set_Primary_Alive (True);
      return True;
   exception
      when others =>
         begin Close_Socket (Sock); exception when others => null; end;
         State.Sync_Errors := State.Sync_Errors + 1;
         Shared_State.Inc_Sync_Errors;
         State.Is_Primary_Alive := False;
         Shared_State.Set_Primary_Alive (False);
         return False;
   end Check_Primary_Health;

   -- =========================================================
   --  Sync z Primary
   -- =========================================================
   procedure Sync_From_Primary (State : in out Shadow_State) is
      Sock  : Socket_Type;
      Addr  : Sock_Addr_Type;
      Req   : constant String :=
         "GET /metrics HTTP/1.0" & ASCII.CR & ASCII.LF &
         "Host: localhost" & ASCII.CR & ASCII.LF &
         ASCII.CR & ASCII.LF;
      Buf   : Stream_Element_Array (1 .. 2048);
      Last  : Stream_Element_Offset;
   begin
      Create_Socket (Sock);
      Set_Socket_Option (Sock, Socket_Level, (Receive_Timeout, 3.0));
      Addr.Addr := Inet_Addr ("127.0.0.1");
      Addr.Port := Port_Type (Primary_Port);
      Connect_Socket (Sock, Addr);
      declare
         Chan : Stream_Access := Stream (Sock);
      begin
         String'Write (Chan, Req);
         Receive_Socket (Sock, Buf, Last);
      end;
      Close_Socket (Sock);
      Log ("SHADOW", "Sync OK: " & Integer'Image (State.Synced_Coins) & " mincu");
   exception
      when others =>
         begin Close_Socket (Sock); exception when others => null; end;
         State.Sync_Errors := State.Sync_Errors + 1;
         Log ("SHADOW", "Sync chyba #" & Integer'Image (State.Sync_Errors));
   end Sync_From_Primary;

   -- =========================================================
   --  Prometheus HTTP server — permanentní task na portu 9303
   -- =========================================================
   task Metrics_Server;

   task body Metrics_Server is
      Server  : Socket_Type;
      Client  : Socket_Type;
      Addr    : Sock_Addr_Type;
      C_Addr  : Sock_Addr_Type;
      Buf     : Stream_Element_Array (1 .. 256);
      Last    : Stream_Element_Offset;
   begin
      Create_Socket (Server);
      Set_Socket_Option (Server, Socket_Level, (Reuse_Address, True));
      Addr.Addr := Any_Inet_Addr;
      Addr.Port := Port_Type (Shadow_Port);
      Bind_Socket (Server, Addr);
      Listen_Socket (Server, 5);
      Log ("SHADOW", "Prometheus server posloucha na portu 9303");
      loop
         begin
            Accept_Socket (Server, Client, C_Addr);
            declare
               Mode_Str   : constant String :=
                  (if Shared_State.Get_Mode = Primary then "1" else "0");
               Alive_Str  : constant String :=
                  (if Shared_State.Get_Primary_Alive then "1" else "0");
               Errors_Str : constant String :=
                  Integer'Image (Shared_State.Get_Sync_Errors);
               Coins_Str  : constant String :=
                  Integer'Image (Shared_State.Get_Coins);
               Mbody : constant String :=
                  "# HELP shadow_is_primary Je Shadow Node primarni?" & ASCII.LF &
                  "shadow_is_primary " & Mode_Str & ASCII.LF &
                  "# HELP shadow_primary_health Zdravi Primary Node" & ASCII.LF &
                  "shadow_primary_health " & Alive_Str & ASCII.LF &
                  "# HELP shadow_sync_errors_total Chyby synchronizace" & ASCII.LF &
                  "shadow_sync_errors_total " & Errors_Str & ASCII.LF &
                  "# HELP shadow_synced_coins Pocet mincu" & ASCII.LF &
                  "shadow_synced_coins " & Coins_Str & ASCII.LF;
               Resp : constant String :=
                  "HTTP/1.0 200 OK" & ASCII.CR & ASCII.LF &
                  "Content-Type: text/plain; version=0.0.4" & ASCII.CR & ASCII.LF &
                  "Content-Length: " & Integer'Image (Mbody'Length) & ASCII.CR & ASCII.LF &
                  ASCII.CR & ASCII.LF & Mbody;
               Chan : Stream_Access := Stream (Client);
            begin
               Receive_Socket (Client, Buf, Last);
               String'Write (Chan, Resp);
               Close_Socket (Client);
            end;
         exception
            when others =>
               begin Close_Socket (Client); exception when others => null; end;
         end;
      end loop;
   end Metrics_Server;

   -- =========================================================
   --  FAILOVER
   -- =========================================================
   procedure Become_Primary (State : in out Shadow_State) is
   begin
      Put_Line ("============================================================");
      Put_Line ("FAILOVER EVENT - SHADOW NODE PREBIRA KONTROLU!");
      Put_Line ("============================================================");
      State.Mode := Primary;
      Shared_State.Set_Mode (Primary);
      Log ("SHADOW->PRIMARY", "Status zmenen na PRIMARY");
      Log ("SHADOW->PRIMARY", "Mincu: " & Integer'Image (State.Synced_Coins));
      Put_Line ("============================================================");
   end Become_Primary;

   procedure Demote_To_Shadow (State : in out Shadow_State) is
   begin
      if State.Mode = Primary then
         Put_Line ("============================================================");
         Put_Line ("PRIMARY NODE SE VRATIL - Vracim se do Shadow modu");
         Put_Line ("============================================================");
         State.Mode := Shadow;
         Shared_State.Set_Mode (Shadow);
         Log ("PRIMARY->SHADOW", "Kontrola predana zpet Primary Node");
         Put_Line ("============================================================");
      end if;
   end Demote_To_Shadow;

   -- =========================================================
   --  Hlavní smyčka
   -- =========================================================
   procedure Run is
      State          : Shadow_State;
      Last_Heartbeat : Time := Clock;
      Primary_Alive  : Boolean;
   begin
      Put_Line ("============================================================");
      Put_Line ("SHADOW NODE - STINOVACI UZEL");
      Put_Line ("============================================================");
      Log ("SHADOW", "Prometheus endpoint: http://localhost:9303/metrics");
      Log ("SHADOW", "Monitoring Primary:  http://localhost:9302/metrics");
      Log ("SHADOW", "Heartbeat interval:   " & Integer'Image (Heartbeat_Sec) & "s");
      Log ("SHADOW", "Failover timeout:     " & Integer'Image (Failover_Timeout) & "s");
      Log ("SHADOW", "Standard 700: 12g stribra");
      Put_Line ("============================================================");
      Put_Line ("[SHADOW] Spoustim monitoring loop...");

      loop
         State.Cycle := State.Cycle + 1;
         Primary_Alive := Check_Primary_Health (State);

         if not Primary_Alive then
            if (Clock - Last_Heartbeat) > Duration (Failover_Timeout)
               and State.Mode = Shadow
            then
               Become_Primary (State);
            end if;
         else
            Last_Heartbeat := Clock;
            Demote_To_Shadow (State);
         end if;

         if State.Mode = Shadow then
            Sync_From_Primary (State);
         end if;

         if State.Cycle mod 10 = 0 then
            Log ((if State.Mode = Primary then "PRIMARY" else "SHADOW"),
                 "Cycle " & Integer'Image (State.Cycle) &
                 " | Primary: " & (if Primary_Alive then "ALIVE" else "DEAD"));
         end if;

         delay Duration (Heartbeat_Sec);
      end loop;
   end Run;

end Shadow_Node;
