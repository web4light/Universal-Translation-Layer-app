--  =============================================================================
--  Sovereign_Local_Vault_Airgap_Guard Body (SPARK 2022 / DO-178C DAL-A)
--  =============================================================================

package body Sovereign_Local_Vault_Airgap_Guard with
  SPARK_Mode => On
is

   procedure Initialize_Vault
     (Vault : out Vault_Record)
   is
   begin
      Vault.Active_Partition   := Partition_Sovereign_Airgap;
      Vault.Stored_Blocks      := 0;
      Vault.Total_Stored_Bytes := 0;
      Vault.Outbound_Net_Bytes := 0;
      Vault.Is_Airgap_Sealed   := True;
      Vault.Is_Sanitized       := True;
   end Initialize_Vault;

   procedure Store_Airgap_Block
     (Vault    : in out Vault_Record;
      Size     : in     Transfer_Size;
      Accepted : out    Boolean)
   is
   begin
      if Vault.Stored_Blocks < Block_Count'Last and then
         Vault.Total_Stored_Bytes <= Natural'Last - Size and then
         Vault.Active_Partition = Partition_Sovereign_Airgap and then
         Vault.Is_Airgap_Sealed
      then
         Vault.Stored_Blocks      := Vault.Stored_Blocks + 1;
         Vault.Total_Stored_Bytes := Vault.Total_Stored_Bytes + Size;
         Vault.Outbound_Net_Bytes := 0;
         Vault.Is_Airgap_Sealed   := True;
         Vault.Is_Sanitized       := False;
         Accepted                 := True;
      else
         Accepted := False;
      end if;
   end Store_Airgap_Block;

   procedure Purge_Ephemeral_Scratch
     (Vault   : in out Vault_Record;
      Cleaned : out    Boolean)
   is
   begin
      Vault.Outbound_Net_Bytes := 0;
      Vault.Is_Airgap_Sealed   := True;
      Vault.Is_Sanitized       := True;
      Cleaned                  := True;
   end Purge_Ephemeral_Scratch;

end Sovereign_Local_Vault_Airgap_Guard;
