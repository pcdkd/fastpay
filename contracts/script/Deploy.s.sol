// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/FastPayCore.sol";

/**
 * @title DeployScript
 * @notice Deployment script for FastPayCore contract
 * @dev Usage:
 *
 *   Base Sepolia (testnet):
 *   forge script script/Deploy.s.sol:DeployScript \
 *     --rpc-url base_sepolia \
 *     --broadcast \
 *     --verify
 *
 *   Base Mainnet (production):
 *   forge script script/Deploy.s.sol:DeployScript \
 *     --rpc-url base \
 *     --broadcast \
 *     --verify
 */
contract DeployScript is Script {
    function run() external {
        // Load deployer private key from environment
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");

        // Get chain ID to determine network
        uint256 chainId = block.chainid;
        string memory networkName;
        string memory explorerUrl;

        if (chainId == 84532) {
            networkName = "Base Sepolia (Testnet)";
            explorerUrl = "https://sepolia.basescan.org";
        } else if (chainId == 8453) {
            networkName = "Base Mainnet";
            explorerUrl = "https://basescan.org";
        } else {
            networkName = "Unknown Network";
            explorerUrl = "https://basescan.org";
        }

        // Start broadcasting transactions
        vm.startBroadcast(deployerPrivateKey);

        // Deploy FastPayCore
        FastPayCore fastPay = new FastPayCore();

        console.log("====================================");
        console.log("FastPayCore deployed to:", address(fastPay));
        console.log("====================================");
        console.log("");
        console.log("Deployment Summary:");
        console.log("  Contract: FastPayCore");
        console.log("  Network:", networkName);
        console.log("  Chain ID:", chainId);
        console.log("  Address:", address(fastPay));
        console.log("");
        console.log("Explorer:");
        console.log("  ", string.concat(explorerUrl, "/address/", vm.toString(address(fastPay))));
        console.log("");
        console.log("Next Steps:");
        console.log("  1. Verify contract on Basescan (if --verify flag used)");
        console.log("  2. Update agents/.env with FASTPAY_ADDRESS=", address(fastPay));
        console.log("  3. Fund test wallets with ETH (merchant) and USDC (customer)");
        console.log("  4. Run agent demo: cd agents && npm run demo");
        console.log("");

        vm.stopBroadcast();
    }
}
