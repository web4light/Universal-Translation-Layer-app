pragma SPARK_Mode (On);

package Stardust_Resonance_Codec is

   type Session_ID_Type is range 0 .. 100_000;
   type Participant_ID_Type is range 1 .. 10_000;
   type Byte is mod 256;
   type Buffer_Index is range 1 .. 128;
   subtype Length_Type is Natural range 0 .. 128;
   type Buffer_Array is array (Buffer_Index) of Byte;
   type Resonance_Frequency_Type is range 432 .. 528;

   type Conversation_Session is record
      Active         : Boolean;
      Session_ID     : Session_ID_Type;
      Owner_ID       : Participant_ID_Type;
      Peer_ID        : Participant_ID_Type;
      Data_Length    : Length_Type;
      Payload        : Buffer_Array;
      Resonance_Freq : Resonance_Frequency_Type;
      Is_Purged      : Boolean;
   end record;

   procedure Initialize_Session
     (Session : out Conversation_Session;
      S_ID    : in  Session_ID_Type;
      Owner   : in  Participant_ID_Type;
      Peer    : in  Participant_ID_Type;
      Freq    : in  Resonance_Frequency_Type)
   with
     Global => null,
     Depends => (Session => (S_ID, Owner, Peer, Freq)),
     Post =>
       Session.Active and then
       not Session.Is_Purged and then
       Session.Session_ID = S_ID and then
       Session.Owner_ID = Owner and then
       Session.Peer_ID = Peer and then
       Session.Resonance_Freq = Freq and then
       Session.Data_Length = 0 and then
       (for all I in Buffer_Index => Session.Payload (I) = 0);

   procedure Process_Inbound_Packet
     (Session            : in out Conversation_Session;
      Requester          : in     Participant_ID_Type;
      Incoming_Data      : in     Buffer_Array;
      Incoming_Len       : in     Length_Type;
      Cleartext_Out      : out    Buffer_Array;
      Cleartext_Len      : out    Length_Type;
      Stardust_Resonance : out    Boolean)
   with
     Global => null,
     Depends =>
       (Session            =>+ (Requester, Incoming_Data, Incoming_Len),
        Cleartext_Out      => (Requester, Incoming_Data, Session),
        Cleartext_Len      => (Requester, Incoming_Len, Session),
        Stardust_Resonance => (Requester, Session)),
     Pre => Session.Active and then not Session.Is_Purged,
     Post =>
       (if Requester = Session.Owner_ID or Requester = Session.Peer_ID then
          not Stardust_Resonance and then
          Cleartext_Len = Incoming_Len and then
          Session.Data_Length = Incoming_Len
        else
          Stardust_Resonance and then
          Cleartext_Len = 0 and then
          (for all I in Buffer_Index => Cleartext_Out (I) = 0));

   procedure Purge_And_Zeroize_RAM
     (Session : in out Conversation_Session)
   with
     Global => null,
     Depends => (Session =>+ null),
     Post =>
       not Session.Active and then
       Session.Is_Purged and then
       Session.Data_Length = 0 and then
       (for all I in Buffer_Index => Session.Payload (I) = 0);

end Stardust_Resonance_Codec;
