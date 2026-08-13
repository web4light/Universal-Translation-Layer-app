-- ============================================================
--  Prometheus Metrics Server — HTTP endpoint na portu 9306
--
--  I/O část — pragma SPARK_Mode (Off)
--  Volá SPARK-proved funkce z Prometheus_Exporter.
--
--  Prometheus scrapuje GET /metrics → vrací text/plain
--  s metrikami ve formátu:
--    # HELP asgard_service_up Jistič služby (1=ON, 0=OFF)
--    # TYPE asgard_service_up gauge
--    asgard_service_up{service="shadow_node"} 1
--
--  Autor: Pan Jeskyně
-- ============================================================

pragma SPARK_Mode (Off);

with Ada.Text_IO;
with Ada.Strings.Fixed;
with Ada.Strings.Unbounded;
with Ada.Streams;
with Ada.Calendar;
with GNAT.Sockets;
with Prometheus_Exporter; use Prometheus_Exporter;

procedure Prometheus_Server is

   use Ada.Text_IO;
   use GNAT.Sockets;

   -- Aktuální snapshot — živý stav systému
   Current : Metrics_Snapshot;
   Start_Time : Ada.Calendar.Time;

   -- Pomocné: Natural → String bez mezer
   function Img (N : Natural) return String is
      Raw : constant String := Natural'Image (N);
   begin
      -- Image vrací " 42", chceme "42"
      return Ada.Strings.Fixed.Trim (Raw, Ada.Strings.Left);
   end Img;

   -- Pomocné: Service_ID → malý string pro label
   function Service_Label (S : Service_ID) return String is
   begin
      case S is
         when Shadow_Node     => return "shadow_node";
         when Watchdog        => return "watchdog";
         when Privacy_423     => return "privacy_423";
         when Asgard_API      => return "asgard_api";
         when Cave_Lab        => return "cave_lab";
         when Faucet_DNS      => return "faucet_dns";
         when Prometheus_Self => return "prometheus";
         when Grafana         => return "grafana";
      end case;
   end Service_Label;

   -- Vygeneruj metrics (Prometheus text format 0.0.4)
   function Generate_Metrics return String is
      NL : constant String := (1 => ASCII.LF);
      Buf : Ada.Strings.Unbounded.Unbounded_String;

      use Ada.Strings.Unbounded;
   begin
      -- Hlavička
      Append (Buf, "# HELP asgard_service_up Jistic sluzby (1=ON, 0=OFF)" & NL);
      Append (Buf, "# TYPE asgard_service_up gauge" & NL);

      for S in Service_ID loop
         declare
            Val : constant String :=
              (if Get_Service (Current, S) = Up then "1" else "0");
         begin
            Append (Buf, "asgard_service_up{service=""" &
                    Service_Label (S) & """} " & Val & NL);
         end;
      end loop;

      Append (Buf, NL);
      Append (Buf, "# HELP asgard_services_total Pocet sluzeb nahore" & NL);
      Append (Buf, "# TYPE asgard_services_total gauge" & NL);
      Append (Buf, "asgard_services_total " & Img (Count_Up (Current)) & NL);

      Append (Buf, NL);
      Append (Buf, "# HELP asgard_all_up Vsechny jistice nahore (1/0)" & NL);
      Append (Buf, "# TYPE asgard_all_up gauge" & NL);
      Append (Buf, "asgard_all_up " &
              (if All_Up (Current) then "1" else "0") & NL);

      Append (Buf, NL);
      Append (Buf, "# HELP asgard_translations_total Celkem prekladu" & NL);
      Append (Buf, "# TYPE asgard_translations_total counter" & NL);
      Append (Buf, "asgard_translations_total " &
              Img (Current.Translations_Total) & NL);

      Append (Buf, NL);
      Append (Buf, "# HELP asgard_dubbing_segments Dabingovych segmentu" & NL);
      Append (Buf, "# TYPE asgard_dubbing_segments counter" & NL);
      Append (Buf, "asgard_dubbing_segments " &
              Img (Current.Dubbing_Segments) & NL);

      Append (Buf, NL);
      Append (Buf, "# HELP asgard_spark_proved SPARK proved checks" & NL);
      Append (Buf, "# TYPE asgard_spark_proved gauge" & NL);
      Append (Buf, "asgard_spark_proved " &
              Img (Current.Spark_Proved) & NL);

      Append (Buf, NL);
      Append (Buf, "# HELP asgard_uptime_seconds Uptime v sekundach" & NL);
      Append (Buf, "# TYPE asgard_uptime_seconds counter" & NL);
      Append (Buf, "asgard_uptime_seconds " &
              Img (Current.Uptime_Seconds) & NL);

      Append (Buf, NL);
      Append (Buf, "# HELP asgard_active_users Aktivnich uzivatelu" & NL);
      Append (Buf, "# TYPE asgard_active_users gauge" & NL);
      Append (Buf, "asgard_active_users " &
              Img (Current.Active_Users) & NL);

      return To_String (Buf);
   end Generate_Metrics;

   -- HTTP response wrapper
   function HTTP_Response (Content : String) return String is
      NL : constant String := (1 => ASCII.CR) & (1 => ASCII.LF);
   begin
      return "HTTP/1.1 200 OK" & NL &
             "Content-Type: text/plain; version=0.0.4; charset=utf-8" & NL &
             "Content-Length:" & Natural'Image (Content'Length) & NL &
             "Connection: close" & NL &
             NL &
             Content;
   end HTTP_Response;

   -- Probe služeb přes TCP connect
   procedure Probe_Services is
      procedure Try_Connect (S : Service_ID; Port : Port_Type) is
         Sock : Socket_Type;
         Addr : Sock_Addr_Type;
      begin
         Create_Socket (Sock);
         Addr.Addr := Inet_Addr ("127.0.0.1");
         Addr.Port := Port;
         Connect_Socket (Sock, Addr);
         Close_Socket (Sock);
         Set_Service (Current, S, Up);
      exception
         when others =>
            Set_Service (Current, S, Down);
            begin
               Close_Socket (Sock);
            exception
               when others => null;
            end;
      end Try_Connect;
   begin
      Try_Connect (Shadow_Node, 9303);
      Try_Connect (Watchdog, 9304);
      Try_Connect (Privacy_423, 9305);
      Try_Connect (Asgard_API, 8000);
      Try_Connect (Cave_Lab, 8001);
      Try_Connect (Faucet_DNS, 8080);
      Try_Connect (Prometheus_Self, 9090);
      Try_Connect (Grafana, 3000);
   end Probe_Services;

   -- Uptime kalkulace
   procedure Update_Uptime is
      use Ada.Calendar;
      Now : constant Time := Clock;
      Elapsed : constant Duration := Now - Start_Time;
      Secs : constant Natural := Natural (Elapsed);
   begin
      if Secs <= 999_999_999 then
         Current.Uptime_Seconds := Secs;
      end if;
   end Update_Uptime;

   -- Hlavní server loop
   Server_Socket : Socket_Type;
   Client_Socket : Socket_Type;
   Address       : Sock_Addr_Type;
   Client_Addr   : Sock_Addr_Type;
   Buffer        : Ada.Streams.Stream_Element_Array (1 .. 4096);
   Last          : Ada.Streams.Stream_Element_Offset;

begin
   Put_Line ("[UP] Prometheus Exporter starting on port" &
             Port_Type'Image (Metrics_Port));

   Start_Time := Ada.Calendar.Clock;

   -- Počáteční stav: 111 proved checks
   Current.Spark_Proved := 111;

   -- Bind na port 9306
   Create_Socket (Server_Socket);
   Set_Socket_Option (Server_Socket, Socket_Level, (Reuse_Address, True));
   Address.Addr := Any_Inet_Addr;
   Address.Port := Metrics_Port;
   Bind_Socket (Server_Socket, Address);
   Listen_Socket (Server_Socket);

   Put_Line ("[UP] Listening on 0.0.0.0:" & Img (Natural (Metrics_Port)));
   Put_Line ("[UP] Zadna nula. Jistic je ON nebo OFF.");

   -- Hlavní smyčka — přijímej HTTP requesty
   loop
      Accept_Socket (Server_Socket, Client_Socket, Client_Addr);

      -- Přečti request (stačí nám vědět že přišel GET)
      Receive_Socket (Client_Socket, Buffer, Last);

      -- Probe služeb + update uptime
      Probe_Services;
      Update_Uptime;

      -- Vygeneruj a pošli response
      declare
         Metrics  : constant String := Generate_Metrics;
         Response : constant String := HTTP_Response (Metrics);
         Data     : Ada.Streams.Stream_Element_Array (1 .. Response'Length);
         for Data'Address use Response'Address;
         pragma Import (Ada, Data);
         Send_Last : Ada.Streams.Stream_Element_Offset;
      begin
         Send_Socket (Client_Socket, Data, Send_Last);
      exception
         when others => null;  -- client disconnect
      end;

      Close_Socket (Client_Socket);
   end loop;

exception
   when E : others =>
      Put_Line ("[X] FATAL: Server error");
      Close_Socket (Server_Socket);
end Prometheus_Server;
