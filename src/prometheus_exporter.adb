-- ============================================================
--  Prometheus Exporter — Implementation
-- ============================================================

pragma SPARK_Mode (On);

package body Prometheus_Exporter is

   procedure Set_Service (Snapshot : in out Metrics_Snapshot;
                          Service  : Service_ID;
                          State    : Service_State) is
   begin
      Snapshot.Services (Service) := State;
   end Set_Service;

   function Get_Service (Snapshot : Metrics_Snapshot;
                         Service  : Service_ID) return Service_State is
   begin
      return Snapshot.Services (Service);
   end Get_Service;

   function All_Up (Snapshot : Metrics_Snapshot) return Boolean is
   begin
      for S in Service_ID loop
         if Snapshot.Services (S) = Down then
            return False;
         end if;
      end loop;
      return True;
   end All_Up;

   function Count_Up (Snapshot : Metrics_Snapshot) return Natural is
      Count : Natural := 0;
   begin
      for S in Service_ID loop
         if Snapshot.Services (S) = Up then
            Count := Count + 1;
         end if;
      end loop;
      return Count;
   end Count_Up;

end Prometheus_Exporter;
