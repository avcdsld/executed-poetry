# Executed Poetry Codex — Contract Source Archive

An archival record of the deployed **Executed Poetry Codex** NFT contracts.

The original source was not kept locally after deployment. These files were
recovered from the verified source code on Etherscan and reassembled into a
Foundry project that recompiles with the **exact settings used on-chain**.

## Deployed contracts (Ethereum mainnet)

| Contract | Address | Etherscan |
| --- | --- | --- |
| `ExecutedPoetryCodex` | `0xb3d5ed7d2ba561bf368ff5191e1c98e9d9ecb954` | [code](https://etherscan.io/address/0xb3d5ed7d2ba561bf368ff5191e1c98e9d9ecb954#code) |
| `ExecutedPoetryRenderer` | `0x51401996b48cB58b8e1F937872e6D56D3cCB9f6A` | [code](https://etherscan.io/address/0x51401996b48cB58b8e1F937872e6D56D3cCB9f6A#code) |

`ExecutedPoetryCodex` is the ERC-721 (name `Executed Poetry Codex`, symbol
`CODEX`, `MAX_SUPPLY = 6`, ERC-2981 royalties). It delegates on-chain
image/thumbnail rendering to `ExecutedPoetryRenderer` via the `IRenderer`
interface.

## Verified compiler settings

These match the Etherscan verification and are pinned in `foundry.toml`:

| Setting | Value |
| --- | --- |
| Compiler | `v0.8.30+commit.73712a01` |
| Optimizer | enabled, `1000` runs |
| Via IR | `true` |
| EVM version | `paris` |
| License (own contracts) | WTFPL |

> Note: the plain optimizer pipeline hits "stack too deep" on the Codex
> contract, confirming the deployment was compiled with the IR pipeline
> (`via_ir = true`).

## Constructor arguments

`ExecutedPoetryRenderer` — no constructor arguments.

`ExecutedPoetryCodex(address _owner, address _renderer, address _royaltyReceiver)`,
ABI-encoded on-chain as:

```
0000000000000000000000001ab4264485188933db0d9bcb34face34d54459be
00000000000000000000000051401996b48cb58b8e1f937872e6d56d3ccb9f6a
0000000000000000000000001ab4264485188933db0d9bcb34face34d54459be
```

Decoded:

| Arg | Value |
| --- | --- |
| `_owner` | `0x1ab4264485188933db0d9bcb34face34d54459be` |
| `_renderer` | `0x51401996b48cB58b8e1F937872e6D56D3cCB9f6A` (the Renderer above) |
| `_royaltyReceiver` | `0x1ab4264485188933db0d9bcb34face34d54459be` |

## Layout

```
codex/
├── foundry.toml                 # compiler settings pinned to the deployment
├── remappings.txt
├── src/                         # the two hand-written contracts
│   ├── ExecutedPoetryCodex.sol
│   └── ExecutedPoetryRenderer.sol
└── deps/                        # vendored, unmodified verified dependency sources
    ├── @openzeppelin/contracts/ # OpenZeppelin Contracts v5.x
    └── solady/src/utils/        # Solady LibString / LibBytes
```

The dependency sources under `deps/` are copied verbatim from the Etherscan
verification (not pulled from a package manager) so the project compiles from
the identical inputs that produced the deployed bytecode.

## Build

```sh
forge build
```

Requires [Foundry](https://book.getfoundry.sh/). No `forge install` step is
needed — all dependencies are vendored in `deps/`.
