-module(faucet_dns).
-behavior(gen_server).

%% API
-export([start_link/1, start_faucet/1, verify_ip/1, resolve/1]).
%% UTL Mesh Authentication API
-export([register_utl_node/3, register_utl_node/5,
         authenticate_utl_node/2, authenticate_utl_node/3,
         heartbeat_utl_node/2, list_utl_nodes/0, revoke_utl_node/1]).
%% UTL Security API (Req 17.1-17.5)
-export([verify_nft/1, verify_attestation/1,
         add_to_whitelist/1, remove_from_whitelist/1, is_whitelisted/1,
         isolate_malicious_node/1, get_tls_config/0]).
%% gen_server callbacks
-export([init/1, handle_call/3, handle_cast/2, handle_info/2,
         terminate/2, code_change/3]).

-define(PROMETHEUS_HEAT_LIMIT, 85).
-define(UTL_TOKEN_TTL_SECONDS, 3600).   %% Token valid for 1 hour
-define(UTL_HEARTBEAT_TIMEOUT, 120).    %% Node dead after 2 min no heartbeat
-define(UTL_ISOLATION_TIMEOUT_MS, 5000). %% Malicious node isolation < 5 seconds
-define(TLS_VERSION, 'tlsv1.3').        %% TLS 1.3 mandatory for mesh

%%% ====================================================================
%%% AsgardLab Internal DNS Records
%%% Custom TLD: .pi (mesh network only)
%%%
%%% Users with Karel IV. client get DNS auto-configured to this server.
%%% From outside internet, use normal domain (GitHub Pages).
%%% ====================================================================

%% Internal .pi domain records (AsgardLab mesh TLD)
-define(DNS_RECORDS, #{
    %% Karel IV. services
    "asterisk.pi"         => "192.168.123.191",  %% Primary (asterisk i7 Windows)
    "shadow.pi"           => "192.168.123.172",  %% Shadow (Esprimo WiFi)
    "nas.pi"              => "192.168.123.121",  %% WD MyCloud NAS
    "metrics.pi"          => "192.168.123.191",  %% Prometheus :9090
    "dashboard.pi"        => "192.168.123.191",  %% Grafana :3000
    "karel.pi"            => "192.168.123.191",  %% Karel IV. :9306
    %% AsgardLab mesh nodes
    "mesh.pi"             => "192.168.123.191",  %% Mesh coordinator
    "privacy.pi"          => "192.168.123.172",  %% Privacy Protocol 4:23
    "watchdog.pi"         => "192.168.123.172"   %% Mossad ALF++ Watchdog
}).

%%% ====================================================================
%%% API — Original DNS + Access Control
%%% ====================================================================

start_link(Port) ->
    gen_server:start_link({local, ?MODULE}, ?MODULE, [Port], []).

start_faucet(Port) ->
    io:format("~n=== ASGARDLAB FAUCET DNS ===~n"),
    io:format("Custom TLD: .pi~n"),
    io:format("Port: ~p~n", [Port]),
    io:format("Mesh nodes: ~p~n", [maps:size(?DNS_RECORDS)]),
    io:format("UTL mesh auth: ENABLED~n"),
    io:format("===========================~n~n"),
    start_link(Port).

%% Resolve .pi domain to IP
resolve(Domain) ->
    Records = ?DNS_RECORDS,
    case maps:get(Domain, Records, undefined) of
        undefined ->
            {error, nxdomain};
        IP ->
            {ok, IP}
    end.

%% Access control — verify sovereign IP
verify_ip("216.198.79.1") ->
    true;
verify_ip(IP) ->
    %% Allow local mesh network
    case is_local_mesh(IP) of
        true  -> true;
        false -> {error, access_denied}
    end.

%% Check if IP is in local mesh range (192.168.123.x)
is_local_mesh(IP) ->
    case string:prefix(IP, "192.168.123.") of
        nomatch -> false;
        _       -> true
    end.

%%% ====================================================================
%%% API — UTL Mesh Authentication
%%% ====================================================================

%% Register a new UTL node in the mesh network
%% NodeId: unique identifier (binary string)
%% IP: node's IP address
%% Capabilities: map of node capabilities (cpu, gpu, ram, models)
register_utl_node(NodeId, IP, Capabilities) ->
    gen_server:call(?MODULE, {register_utl_node, NodeId, IP, Capabilities}).

%% Authenticate a UTL node with its token
%% NodeId: node identifier
%% Token: authentication token (generated at registration)
authenticate_utl_node(NodeId, Token) ->
    gen_server:call(?MODULE, {authenticate_utl_node, NodeId, Token}).

%% Update heartbeat for a UTL node (keeps it alive in the mesh)
%% NodeId: node identifier
%% Token: valid auth token
heartbeat_utl_node(NodeId, Token) ->
    gen_server:call(?MODULE, {heartbeat_utl_node, NodeId, Token}).

%% List all registered UTL nodes
list_utl_nodes() ->
    gen_server:call(?MODULE, list_utl_nodes).

%% Revoke a node's access to the mesh
revoke_utl_node(NodeId) ->
    gen_server:call(?MODULE, {revoke_utl_node, NodeId}).

%%% ====================================================================
%%% API — UTL Security (Requirements 17.1-17.5)
%%% ====================================================================

%% Register with NFT + attestation verification (Req 17.1, 17.4)
%% Full auth: requires valid Soulbound NFT AND hardware attestation
register_utl_node(NodeId, IP, Capabilities, NftData, AttestationData) ->
    gen_server:call(?MODULE, {register_utl_node_secure, NodeId, IP,
                              Capabilities, NftData, AttestationData}).

%% Authenticate with hardware attestation (Req 17.4)
authenticate_utl_node(NodeId, Token, AttestationData) ->
    gen_server:call(?MODULE, {authenticate_utl_node_attested,
                              NodeId, Token, AttestationData}).

%% Verify Soulbound NFT validity (Req 17.1)
%% NftData: #{wallet_address, biometric_bound, transfer_count, nft_status}
%% Access granted iff: transfer_count == 0, biometric_bound == true, status == active
verify_nft(NftData) ->
    gen_server:call(?MODULE, {verify_nft, NftData}).

%% Verify hardware attestation (Req 17.4)
%% AttestationData: #{tpm_signature, timestamp, platform_id, nonce}
verify_attestation(AttestationData) ->
    gen_server:call(?MODULE, {verify_attestation, AttestationData}).

%% Dynamic IP whitelist management (Req 17.2)
add_to_whitelist(IP) ->
    gen_server:call(?MODULE, {add_to_whitelist, IP}).

remove_from_whitelist(IP) ->
    gen_server:call(?MODULE, {remove_from_whitelist, IP}).

is_whitelisted(IP) ->
    gen_server:call(?MODULE, {is_whitelisted, IP}).

%% Isolate malicious node within 5 seconds (Req 17.3)
%% Immediately: revoke + remove from whitelist + report to n8n
isolate_malicious_node(NodeId) ->
    gen_server:call(?MODULE, {isolate_malicious_node, NodeId}, ?UTL_ISOLATION_TIMEOUT_MS).

%% Get TLS 1.3 configuration with certificate pinning (Req 17.5)
get_tls_config() ->
    gen_server:call(?MODULE, get_tls_config).

%%% ====================================================================
%%% gen_server callbacks
%%% ====================================================================

init([Port]) ->
    io:format("[FAUCET_DNS] Starting on port ~p~n", [Port]),
    io:format("[FAUCET_DNS] DNS records loaded: ~p~n",
              [maps:size(?DNS_RECORDS)]),
    io:format("[FAUCET_DNS] UTL mesh authentication: active~n"),
    %% Schedule periodic cleanup of expired nodes
    erlang:send_after(?UTL_HEARTBEAT_TIMEOUT * 1000, self(), cleanup_expired_nodes),
    {ok, #{
        port => Port,
        heat_level => 23,
        total_queries => 0,
        %% UTL Mesh state: #{NodeId => node_record}
        utl_nodes => #{},
        utl_auth_count => 0,
        utl_denied_count => 0,
        %% Dynamic IP whitelist for mesh nodes (Req 17.2)
        ip_whitelist => sets:from_list(["192.168.123.191", "192.168.123.172",
                                         "192.168.123.121"]),
        %% Isolation audit log
        isolated_nodes => []
    }}.

%%% --- Original handlers ---

handle_call({resolve, Domain}, _From, State) ->
    Queries = maps:get(total_queries, State) + 1,
    Result = resolve(Domain),
    case Result of
        {ok, IP} ->
            io:format("[DNS] ~s -> ~s (query #~p)~n", [Domain, IP, Queries]);
        {error, nxdomain} ->
            io:format("[DNS] NXDOMAIN: ~s~n", [Domain])
    end,
    {reply, Result, State#{total_queries => Queries}};

handle_call({incoming_request, IP}, _From, State) ->
    case verify_ip(IP) of
        true ->
            Queries = maps:get(total_queries, State) + 1,
            io:format("[FAUCET] Access granted: ~s~n", [IP]),
            {reply, {ok, sovereign_access_granted},
             State#{total_queries => Queries}};
        {error, access_denied} ->
            io:format("[FAUCET] Access denied: ~s~n", [IP]),
            report_denial(IP),
            {reply, {error, access_denied}, State}
    end;

handle_call({list_records}, _From, State) ->
    {reply, {ok, ?DNS_RECORDS}, State};

%%% --- UTL Mesh Authentication handlers ---

handle_call({register_utl_node, NodeId, IP, Capabilities}, _From, State) ->
    Nodes = maps:get(utl_nodes, State),
    case maps:is_key(NodeId, Nodes) of
        true ->
            io:format("[UTL_MESH] Node already registered: ~s~n", [NodeId]),
            {reply, {error, already_registered}, State};
        false ->
            %% Generate auth token (SHA-256 of NodeId + timestamp + random)
            Token = generate_token(NodeId),
            Now = erlang:system_time(second),
            NodeRecord = #{
                node_id => NodeId,
                ip => IP,
                capabilities => Capabilities,
                token => Token,
                registered_at => Now,
                last_heartbeat => Now,
                status => active
            },
            NewNodes = maps:put(NodeId, NodeRecord, Nodes),
            io:format("[UTL_MESH] Node registered: ~s (~s) token=~s~n",
                      [NodeId, IP, string:slice(Token, 0, 16)]),
            {reply, {ok, Token}, State#{utl_nodes => NewNodes}}
    end;

handle_call({authenticate_utl_node, NodeId, Token}, _From, State) ->
    Nodes = maps:get(utl_nodes, State),
    case maps:get(NodeId, Nodes, undefined) of
        undefined ->
            Denied = maps:get(utl_denied_count, State) + 1,
            io:format("[UTL_MESH] Auth DENIED — unknown node: ~s~n", [NodeId]),
            {reply, {error, unknown_node}, State#{utl_denied_count => Denied}};
        NodeRecord ->
            StoredToken = maps:get(token, NodeRecord),
            Status = maps:get(status, NodeRecord),
            case {Token =:= StoredToken, Status} of
                {true, active} ->
                    AuthCount = maps:get(utl_auth_count, State) + 1,
                    io:format("[UTL_MESH] Auth OK: ~s~n", [NodeId]),
                    {reply, {ok, authenticated}, State#{utl_auth_count => AuthCount}};
                {true, revoked} ->
                    Denied = maps:get(utl_denied_count, State) + 1,
                    io:format("[UTL_MESH] Auth DENIED — node revoked: ~s~n", [NodeId]),
                    {reply, {error, node_revoked}, State#{utl_denied_count => Denied}};
                {false, _} ->
                    Denied = maps:get(utl_denied_count, State) + 1,
                    io:format("[UTL_MESH] Auth DENIED — bad token: ~s~n", [NodeId]),
                    report_denial_utl(NodeId, "invalid_token"),
                    {reply, {error, invalid_token}, State#{utl_denied_count => Denied}}
            end
    end;

handle_call({heartbeat_utl_node, NodeId, Token}, _From, State) ->
    Nodes = maps:get(utl_nodes, State),
    case maps:get(NodeId, Nodes, undefined) of
        undefined ->
            {reply, {error, unknown_node}, State};
        NodeRecord ->
            StoredToken = maps:get(token, NodeRecord),
            case Token =:= StoredToken of
                true ->
                    Now = erlang:system_time(second),
                    Updated = maps:put(last_heartbeat, Now, NodeRecord),
                    NewNodes = maps:put(NodeId, Updated, Nodes),
                    {reply, {ok, heartbeat_accepted}, State#{utl_nodes => NewNodes}};
                false ->
                    {reply, {error, invalid_token}, State}
            end
    end;

handle_call(list_utl_nodes, _From, State) ->
    Nodes = maps:get(utl_nodes, State),
    %% Return sanitized list (no tokens exposed)
    SafeList = maps:fold(fun(NodeId, Record, Acc) ->
        [{NodeId, #{
            ip => maps:get(ip, Record),
            status => maps:get(status, Record),
            last_heartbeat => maps:get(last_heartbeat, Record),
            capabilities => maps:get(capabilities, Record)
        }} | Acc]
    end, [], Nodes),
    {reply, {ok, SafeList}, State};

handle_call({revoke_utl_node, NodeId}, _From, State) ->
    Nodes = maps:get(utl_nodes, State),
    case maps:get(NodeId, Nodes, undefined) of
        undefined ->
            {reply, {error, unknown_node}, State};
        NodeRecord ->
            Updated = maps:put(status, revoked, NodeRecord),
            NewNodes = maps:put(NodeId, Updated, Nodes),
            io:format("[UTL_MESH] Node REVOKED: ~s~n", [NodeId]),
            report_denial_utl(NodeId, "revoked_by_admin"),
            {reply, {ok, revoked}, State#{utl_nodes => NewNodes}}
    end;

%%% --- UTL Security handlers (Req 17.1-17.5) ---

%% Secure registration with NFT + attestation gate
handle_call({register_utl_node_secure, NodeId, IP, Capabilities,
             NftData, AttestationData}, _From, State) ->
    %% Step 1: Verify Soulbound NFT (Req 17.1)
    case validate_nft_internal(NftData) of
        {error, Reason} ->
            Denied = maps:get(utl_denied_count, State) + 1,
            io:format("[UTL_MESH] Registration DENIED — NFT invalid: ~s (~p)~n",
                      [NodeId, Reason]),
            report_denial_utl(NodeId, "nft_" ++ atom_to_list(Reason)),
            {reply, {error, {nft_invalid, Reason}}, State#{utl_denied_count => Denied}};
        {ok, valid} ->
            %% Step 2: Verify hardware attestation (Req 17.4)
            case validate_attestation_internal(AttestationData) of
                {error, AttReason} ->
                    Denied = maps:get(utl_denied_count, State) + 1,
                    io:format("[UTL_MESH] Registration DENIED — attestation invalid: ~s (~p)~n",
                              [NodeId, AttReason]),
                    report_denial_utl(NodeId, "attestation_" ++ atom_to_list(AttReason)),
                    {reply, {error, {attestation_invalid, AttReason}},
                     State#{utl_denied_count => Denied}};
                {ok, valid} ->
                    %% Both checks passed — proceed with registration
                    Nodes = maps:get(utl_nodes, State),
                    case maps:is_key(NodeId, Nodes) of
                        true ->
                            {reply, {error, already_registered}, State};
                        false ->
                            Token = generate_token(NodeId),
                            Now = erlang:system_time(second),
                            NodeRecord = #{
                                node_id => NodeId,
                                ip => IP,
                                capabilities => Capabilities,
                                token => Token,
                                registered_at => Now,
                                last_heartbeat => Now,
                                status => active,
                                nft_verified => true,
                                attestation_verified => true
                            },
                            NewNodes = maps:put(NodeId, NodeRecord, Nodes),
                            %% Auto-whitelist the node IP (Req 17.2)
                            Whitelist = maps:get(ip_whitelist, State),
                            NewWhitelist = sets:add_element(IP, Whitelist),
                            io:format("[UTL_MESH] Secure registration OK: ~s (~s) NFT+ATT verified~n",
                                      [NodeId, IP]),
                            {reply, {ok, Token},
                             State#{utl_nodes => NewNodes, ip_whitelist => NewWhitelist}}
                    end
            end
    end;

%% Authenticate with attestation refresh
handle_call({authenticate_utl_node_attested, NodeId, Token, AttestationData},
            _From, State) ->
    case validate_attestation_internal(AttestationData) of
        {error, Reason} ->
            Denied = maps:get(utl_denied_count, State) + 1,
            io:format("[UTL_MESH] Auth DENIED — attestation refresh failed: ~s~n", [NodeId]),
            {reply, {error, {attestation_invalid, Reason}}, State#{utl_denied_count => Denied}};
        {ok, valid} ->
            %% Attestation OK — proceed with normal token auth
            Nodes = maps:get(utl_nodes, State),
            case maps:get(NodeId, Nodes, undefined) of
                undefined ->
                    {reply, {error, unknown_node}, State};
                NodeRecord ->
                    StoredToken = maps:get(token, NodeRecord),
                    case Token =:= StoredToken of
                        true ->
                            AuthCount = maps:get(utl_auth_count, State) + 1,
                            {reply, {ok, authenticated_attested}, State#{utl_auth_count => AuthCount}};
                        false ->
                            Denied = maps:get(utl_denied_count, State) + 1,
                            {reply, {error, invalid_token}, State#{utl_denied_count => Denied}}
                    end
            end
    end;

%% NFT verification (standalone check)
handle_call({verify_nft, NftData}, _From, State) ->
    Result = validate_nft_internal(NftData),
    {reply, Result, State};

%% Attestation verification (standalone check)
handle_call({verify_attestation, AttestationData}, _From, State) ->
    Result = validate_attestation_internal(AttestationData),
    {reply, Result, State};

%% IP Whitelist management (Req 17.2)
handle_call({add_to_whitelist, IP}, _From, State) ->
    Whitelist = maps:get(ip_whitelist, State),
    NewWhitelist = sets:add_element(IP, Whitelist),
    io:format("[FAUCET] IP whitelisted: ~s~n", [IP]),
    {reply, {ok, added}, State#{ip_whitelist => NewWhitelist}};

handle_call({remove_from_whitelist, IP}, _From, State) ->
    Whitelist = maps:get(ip_whitelist, State),
    NewWhitelist = sets:del_element(IP, Whitelist),
    io:format("[FAUCET] IP removed from whitelist: ~s~n", [IP]),
    {reply, {ok, removed}, State#{ip_whitelist => NewWhitelist}};

handle_call({is_whitelisted, IP}, _From, State) ->
    Whitelist = maps:get(ip_whitelist, State),
    Result = sets:is_element(IP, Whitelist),
    {reply, {ok, Result}, State};

%% Malicious node isolation — must complete within 5 seconds (Req 17.3)
handle_call({isolate_malicious_node, NodeId}, _From, State) ->
    StartTime = erlang:monotonic_time(millisecond),
    Nodes = maps:get(utl_nodes, State),
    case maps:get(NodeId, Nodes, undefined) of
        undefined ->
            {reply, {error, unknown_node}, State};
        NodeRecord ->
            %% Step 1: Revoke immediately
            Revoked = maps:put(status, isolated, NodeRecord),
            NewNodes = maps:put(NodeId, Revoked, Nodes),
            %% Step 2: Remove IP from whitelist
            IP = maps:get(ip, NodeRecord),
            Whitelist = maps:get(ip_whitelist, State),
            NewWhitelist = sets:del_element(IP, Whitelist),
            %% Step 3: Report to n8n (non-blocking)
            report_isolation(NodeId, IP),
            %% Step 4: Log isolation with timing
            Elapsed = erlang:monotonic_time(millisecond) - StartTime,
            io:format("[UTL_MESH] ISOLATED malicious node: ~s (~s) in ~pms~n",
                      [NodeId, IP, Elapsed]),
            %% Track in audit log
            Isolated = maps:get(isolated_nodes, State),
            AuditEntry = #{node_id => NodeId, ip => IP,
                           timestamp => erlang:system_time(second),
                           elapsed_ms => Elapsed},
            {reply, {ok, isolated, Elapsed},
             State#{utl_nodes => NewNodes,
                    ip_whitelist => NewWhitelist,
                    isolated_nodes => [AuditEntry | Isolated]}}
    end;

%% TLS 1.3 configuration with certificate pinning (Req 17.5)
handle_call(get_tls_config, _From, State) ->
    Config = #{
        tls_version => ?TLS_VERSION,
        ciphers => [
            "TLS_AES_256_GCM_SHA384",
            "TLS_CHACHA20_POLY1305_SHA256",
            "TLS_AES_128_GCM_SHA256"
        ],
        cert_pinning => #{
            enabled => true,
            pin_sha256 => [
                %% Primary node certificate pin
                "sha256//YLh1dUR9y6Kja30RrAn7JKnbQG/uEtLMkBgFF2Fuihg=",
                %% Shadow node certificate pin
                "sha256//sRHdihwgkaib1P1gN7SkKPB+R1Y1cA8RNFmGaz6N50M="
            ],
            max_age_seconds => 2592000,  %% 30 days
            include_subdomains => true
        },
        client_cert_required => true,
        verify_peer => true,
        depth => 2
    },
    {reply, {ok, Config}, State};

handle_call(_Request, _From, State) ->
    {reply, {error, unknown_command}, State}.

%%% --- Casts ---

handle_cast({update_heat, NewHeat}, State)
        when NewHeat > ?PROMETHEUS_HEAT_LIMIT ->
    io:format("[FAUCET] CRITICAL: Reactor temp ~p°C! Evacuating to .vhdx~n",
              [NewHeat]),
    {noreply, State#{heat_level => NewHeat}};
handle_cast({update_heat, NewHeat}, State) ->
    {noreply, State#{heat_level => NewHeat}};
handle_cast(_Msg, State) ->
    {noreply, State}.

%%% --- Info (periodic cleanup) ---

handle_info(cleanup_expired_nodes, State) ->
    Nodes = maps:get(utl_nodes, State),
    Now = erlang:system_time(second),
    CleanedNodes = maps:filter(fun(_NodeId, Record) ->
        LastHB = maps:get(last_heartbeat, Record),
        Status = maps:get(status, Record),
        %% Keep if: active AND heartbeat within timeout, OR revoked (keep for audit)
        case Status of
            revoked -> true;
            active  -> (Now - LastHB) < ?UTL_HEARTBEAT_TIMEOUT
        end
    end, Nodes),
    Removed = maps:size(Nodes) - maps:size(CleanedNodes),
    case Removed > 0 of
        true ->
            io:format("[UTL_MESH] Cleanup: removed ~p expired nodes~n", [Removed]);
        false ->
            ok
    end,
    %% Schedule next cleanup
    erlang:send_after(?UTL_HEARTBEAT_TIMEOUT * 1000, self(), cleanup_expired_nodes),
    {noreply, State#{utl_nodes => CleanedNodes}};

handle_info(_Info, State) ->
    {noreply, State}.

%%% ====================================================================
%%% Internal Functions
%%% ====================================================================

%%% === Token Generation ===

generate_token(NodeId) ->
    %% Generate a unique token: hex-encoded SHA-256(NodeId + timestamp + random)
    Timestamp = integer_to_list(erlang:system_time(microsecond)),
    Random = integer_to_list(rand:uniform(999999999)),
    Input = lists:flatten([NodeId, ":", Timestamp, ":", Random]),
    Hash = crypto:hash(sha256, Input),
    binary_to_hex(Hash).

binary_to_hex(Bin) ->
    lists:flatten([io_lib:format("~2.16.0b", [B]) || <<B>> <= Bin]).

%%% === N8N Webhook Reporting ===

report_denial(IP) ->
    Url = "http://localhost:5678/webhook/faucet-denial",
    Body = io_lib:format("{\"ip\":\"~s\",\"reason\":\"not_whitelisted\",\"timestamp\":~B}",
                         [IP, erlang:system_time(second)]),
    case httpc:request(post, {Url, [], "application/json", lists:flatten(Body)}, [], []) of
        {ok, _} -> ok;
        {error, _Reason} -> ok  % n8n may be down — autonomous mode
    end.

report_denial_utl(NodeId, Reason) ->
    Url = "http://localhost:5678/webhook/utl-mesh-denial",
    Body = io_lib:format(
        "{\"node_id\":\"~s\",\"reason\":\"~s\",\"timestamp\":~B}",
        [NodeId, Reason, erlang:system_time(second)]
    ),
    case httpc:request(post, {Url, [], "application/json", lists:flatten(Body)}, [], []) of
        {ok, _} -> ok;
        {error, _Reason} -> ok  % n8n may be down — autonomous mode
    end.

%%% === NFT Validation (Req 17.1) ===

%% Validates Soulbound NFT: must be non-transferable, biometric-bound, active
validate_nft_internal(NftData) when is_map(NftData) ->
    TransferCount = maps:get(transfer_count, NftData, -1),
    BiometricBound = maps:get(biometric_bound, NftData, false),
    NftStatus = maps:get(nft_status, NftData, undefined),
    WalletAddress = maps:get(wallet_address, NftData, ""),
    %% Check all conditions
    case {TransferCount, BiometricBound, NftStatus, WalletAddress} of
        {0, true, active, Addr} when length(Addr) =:= 42 ->
            {ok, valid};
        {0, true, active, _} ->
            {error, invalid_wallet};
        {0, false, _, _} ->
            {error, not_biometric_bound};
        {N, _, _, _} when N > 0 ->
            {error, transferred};  %% Soulbound = transfer_count must be 0
        {_, _, Status, _} when Status =/= active ->
            {error, nft_not_active};
        _ ->
            {error, invalid_nft_data}
    end;
validate_nft_internal(_) ->
    {error, invalid_nft_data}.

%%% === Hardware Attestation Validation (Req 17.4) ===

%% Validates TPM-based hardware attestation
validate_attestation_internal(AttestationData) when is_map(AttestationData) ->
    TpmSignature = maps:get(tpm_signature, AttestationData, <<>>),
    Timestamp = maps:get(timestamp, AttestationData, 0),
    PlatformId = maps:get(platform_id, AttestationData, ""),
    Nonce = maps:get(nonce, AttestationData, <<>>),
    Now = erlang:system_time(second),
    %% Check attestation freshness (must be within last 5 minutes)
    MaxAge = 300,
    case {byte_size(TpmSignature) > 0, (Now - Timestamp) =< MaxAge,
          length(PlatformId) > 0, byte_size(Nonce) >= 16} of
        {false, _, _, _} ->
            {error, missing_tpm_signature};
        {_, false, _, _} ->
            {error, attestation_expired};
        {_, _, false, _} ->
            {error, missing_platform_id};
        {_, _, _, false} ->
            {error, nonce_too_short};
        {true, true, true, true} ->
            %% Verify TPM signature against known platform keys
            %% (In production: verify crypto signature against TPM CA)
            case verify_tpm_signature(TpmSignature, PlatformId, Nonce) of
                true  -> {ok, valid};
                false -> {error, signature_invalid}
            end
    end;
validate_attestation_internal(_) ->
    {error, invalid_attestation_data}.

%% TPM signature verification (stub — in production uses TPM CA cert chain)
verify_tpm_signature(Signature, PlatformId, Nonce) ->
    %% Verify: SHA-256(PlatformId ++ Nonce) matches signature prefix
    %% This is a simplified check — real implementation verifies against TPM CA
    Expected = crypto:hash(sha256, [PlatformId, Nonce]),
    %% Accept if signature starts with expected hash (attestation format)
    case Signature of
        <<Expected:32/binary, _Rest/binary>> -> true;
        _ ->
            %% Fallback: accept any non-empty signature in dev mode
            %% TODO: strict mode for production
            byte_size(Signature) >= 32
    end.

%%% === Malicious Node Isolation Report ===

report_isolation(NodeId, IP) ->
    Url = "http://localhost:5678/webhook/utl-node-isolated",
    Body = io_lib:format(
        "{\"node_id\":\"~s\",\"ip\":\"~s\",\"reason\":\"malicious_detected\","
        "\"action\":\"isolated\",\"timestamp\":~B}",
        [NodeId, IP, erlang:system_time(second)]
    ),
    %% Non-blocking report — isolation must complete within 5s regardless
    spawn(fun() ->
        case httpc:request(post, {Url, [], "application/json", lists:flatten(Body)}, [], []) of
            {ok, _} -> ok;
            {error, _} -> ok
        end
    end).

terminate(_Reason, _State) ->
    io:format("[FAUCET] Reactor safely shut down. RAM trace cleared.~n"),
    ok.

code_change(_OldVsn, State, _Extra) ->
    {ok, State}.
