--  =============================================================================
--  Sovereign_Local_Vault_Airgap_Guard (SPARK 2022 / DO-178C DAL-A)
--  Sovereign Web 4.23 & UGREEN AI NAS Integration: Airgapped Sovereign Storage.
--  Formal invariant enforcement for zero-leak local NAS isolation (Outbound_Bytes = 0),
--  partition access integrity, and ephemeral scratch zeroization at 04:23 UTC.
--  =============================================================================

package Sovereign_Local_Vault_Airgap_Guard with
  SPARK_Mode => On
is

   subtype Block_Count is Natural range 0 .. 1_000_000;
   subtype Transfer_Size is Positive range 1 .. 65_536;

   type Vault_Partition is
     (Partition_Public_Share,
      Partition_Sovereign_Airgap,
      Partition_Ephemeral_Scratch);

   type Vault_Record is record
      Active_Partition    : Vault_Partition;
      Stored_Blocks       : Block_Count;
      Total_Stored_Bytes  : Natural;
      Outbound_Net_Bytes  : Natural;
      Is_Airgap_Sealed    : Boolean;
      Is_Sanitized        : Boolean;
   end record;

   --  Initialize pristine sovereign vault airgap state
   procedure Initialize_Vault
     (Vault : out Vault_Record)
   with
     Global => null,
     Post   => Vault.Active_Partition = Partition_Sovereign_Airgap and
               Vault.Stored_Blocks = 0 and
               Vault.Total_Stored_Bytes = 0 and
               Vault.Outbound_Net_Bytes = 0 and
               Vault.Is_Airgap_Sealed = True and
               Vault.Is_Sanitized = True;

   --  Write confidential block into airgapped sovereign partition with zero-leak invariant
   procedure Store_Airgap_Block
     (Vault    : in out Vault_Record;
      Size     : in     Transfer_Size;
      Accepted : out    Boolean)
   with
     Global => null,
     Pre    => Vault.Stored_Blocks < Block_Count'Last and
               Vault.Total_Stored_Bytes <= Natural'Last - Size,
     Post   => (if Accepted then
                  Vault.Active_Partition = Partition_Sovereign_Airgap and
                  Vault.Stored_Blocks = Vault.Stored_Blocks'Old + 1 and
                  Vault.Total_Stored_Bytes = Vault.Total_Stored_Bytes'Old + Size and
                  Vault.Outbound_Net_Bytes = 0 and
                  Vault.Is_Airgap_Sealed = True and
                  Vault.Is_Sanitized = False
                else
                  Vault.Stored_Blocks = Vault.Stored_Blocks'Old and
                  Vault.Total_Stored_Bytes = Vault.Total_Stored_Bytes'Old);

   --  Deterministic 04:23 UTC RAM & ephemeral scratch scrub (non-binary zero)
   procedure Purge_Ephemeral_Scratch
     (Vault   : in out Vault_Record;
      Cleaned : out    Boolean)
   with
     Global => null,
     Post   => Vault.Outbound_Net_Bytes = 0 and
               Vault.Is_Airgap_Sealed = True and
               Vault.Is_Sanitized = True and
               Cleaned = True;

end Sovereign_Local_Vault_Airgap_Guard;
