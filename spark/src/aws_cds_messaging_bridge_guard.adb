--  =============================================================================
--  AWS_CDS_Messaging_Bridge_Guard Body (SPARK 2022 / DO-178C DAL-A)
--  =============================================================================

package body AWS_CDS_Messaging_Bridge_Guard with
  SPARK_Mode => On
is

   procedure Initialize_Bridge
     (State : out Bridge_Supervisor_State)
   is
   begin
      State.Active_Channel   := Channel_RCS;
      State.Messages_Sent    := 0;
      State.Total_Bytes_Sent := 0;
      State.Is_Sanitized     := True;
   end Initialize_Bridge;

   procedure Dispatch_Carrier_Message
     (State    : in out Bridge_Supervisor_State;
      Msg      : in     Outbound_Message_Record;
      Accepted : out    Boolean)
   is
   begin
      if (not Msg.Contains_PrivKey) and then
         Msg.Airgap_Shielded and then
         State.Messages_Sent < Natural'Last and then
         State.Total_Bytes_Sent <= Natural'Last - Msg.Length
      then
         State.Active_Channel   := Msg.Channel;
         State.Messages_Sent    := State.Messages_Sent + 1;
         State.Total_Bytes_Sent := State.Total_Bytes_Sent + Msg.Length;
         State.Is_Sanitized     := False;
         Accepted               := True;
      else
         Accepted := False;
      end if;
   end Dispatch_Carrier_Message;

   procedure Purge_Carrier_Session
     (State   : in out Bridge_Supervisor_State;
      Success : out    Boolean)
   is
   begin
      State.Active_Channel := Channel_RCS;
      State.Is_Sanitized   := True;
      Success              := True;
   end Purge_Carrier_Session;

end AWS_CDS_Messaging_Bridge_Guard;
