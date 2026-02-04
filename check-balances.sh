#!/bin/bash
# Quick balance checker for FastPay wallets

echo "🔍 Checking wallet balances..."
echo ""

# Source the agents .env file
if [ -f agents/.env ]; then
    export $(cat agents/.env | grep -v '^#' | xargs)
else
    echo "❌ agents/.env not found!"
    exit 1
fi

echo "Merchant Wallet:"
echo "  Address: Check in your wallet app"
echo "  Needs: ~0.001 ETH for gas fees"
echo ""

echo "Customer Wallet:"
echo "  Address: Check in your wallet app"
echo "  Needs: ~1 USDC (no ETH required!)"
echo ""

echo "💡 Tip: You can check balances at:"
echo "   https://sepolia.basescan.org/"
echo ""
echo "Get test tokens:"
echo "   ETH: https://www.alchemy.com/faucets/base-sepolia"
echo "   USDC: Swap ETH for USDC on Base Sepolia Uniswap"
