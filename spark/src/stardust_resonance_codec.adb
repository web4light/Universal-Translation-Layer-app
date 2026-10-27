pragma SPARK_Mode (On);

package body Stardust_Resonance_Codec is

   procedure Initialize_Session
     (Session : out Conversation_Session;
      S_ID    : in  Session_ID_Type;
      Owner   : in  Participant_ID_Type;
      Peer    : in  Participant_ID_Type;
      Freq    : in  Resonance_Frequency_Type)
   is
   begin
      Session.Active         := True;
      Session.Session_ID     := S_ID;
      Session.Owner_ID       := Owner;
      Session.Peer_ID        := Peer;
      Session.Data_Length    := 0;
      Session.Resonance_Freq := Freq;
      Session.Is_Purged      := False;
      Session.Payload        := (others => 0);
   end Initialize_Session;

   procedure Process_Inbound_Packet
     (Session            : in out Conversation_Session;
      Requester          : in     Participant_ID_Type;
      Incoming_Data      : in     Buffer_Array;
      Incoming_Len       : in     Length_Type;
      Cleartext_Out      : out    Buffer_Array;
      Cleartext_Len      : out    Length_Type;
      Stardust_Resonance : out    Boolean)
   is
   begin
      if Requester = Session.Owner_ID or Requester = Session.Peer_ID then
         Stardust_Resonance  := False;
         Cleartext_Len       := Incoming_Len;
         Session.Data_Length := Incoming_Len;
         Cleartext_Out       := Incoming_Data;
         Session.Payload     := Incoming_Data;
      else
         -- Outside listener: no cleartext access, only resonant stardust sparkle mask
         Stardust_Resonance := True;
         Cleartext_Len      := 0;
         Cleartext_Out      := (others => 0);
      end if;
   end Process_Inbound_Packet;

   procedure Purge_And_Zeroize_RAM
     (Session : in out Conversation_Session)
   is
   begin
      Session.Active      := False;
      Session.Is_Purged   := True;
      Session.Data_Length := 0;
      Session.Payload     := (others => 0);
   end Purge_And_Zeroize_RAM;

end Stardust_Resonance_Codec;
