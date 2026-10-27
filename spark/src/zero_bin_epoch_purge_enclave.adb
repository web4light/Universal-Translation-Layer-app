--  =============================================================================
--  Zero_Bin_Epoch_Purge_Enclave - Implementation
--  =============================================================================

package body Zero_Bin_Epoch_Purge_Enclave with
  SPARK_Mode => On
is

   procedure Initialize_Enclave
     (State : out Enclave_Purge_State)
   is
   begin
      State := (Active_Bytes   => 0,
                Memory_Payload => (others => 0),
                Is_Sanitized   => True,
                Total_Epochs   => 0);
   end Initialize_Enclave;

   procedure Load_Ephemeral_Payload
     (State  : in out Enclave_Purge_State;
      Length : in     Payload_Length;
      Fill   : in     Byte_Value)
   is
   begin
      State.Active_Bytes   := Length;
      State.Memory_Payload := (others => Fill);
      State.Is_Sanitized   := False;
   end Load_Ephemeral_Payload;

   procedure Purge_Memory_Epoch
     (State   : in out Enclave_Purge_State;
      Success : out    Boolean)
   is
   begin
      State.Active_Bytes   := 0;
      State.Memory_Payload := (others => 0);
      State.Is_Sanitized   := True;

      if State.Total_Epochs < Natural'Last then
         State.Total_Epochs := State.Total_Epochs + 1;
         Success            := True;
      else
         Success            := False;
      end if;
   end Purge_Memory_Epoch;

end Zero_Bin_Epoch_Purge_Enclave;
