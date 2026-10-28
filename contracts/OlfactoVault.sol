// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract OlfactoVault {
    struct Record {
        address currentOwner;
        uint256 timestamp;
    }

    // creator (who registered) => commitment => record
    mapping(address => mapping(bytes32 => Record)) private records;

    event Registered(bytes32 indexed commitment, address indexed creator, uint256 timestamp);
    event OwnershipTransferred(bytes32 indexed commitment, address indexed from, address indexed to);

    // Store a commitment = keccak256(owner, vector, salt). Only the hash goes on-chain.
    function register(bytes32 commitment) external {
        require(commitment != bytes32(0), "Empty commitment");
        require(records[msg.sender][commitment].timestamp == 0, "Already registered");
        records[msg.sender][commitment] = Record(msg.sender, block.timestamp);
        emit Registered(commitment, msg.sender, block.timestamp);
    }

    function getRecord(address creator, bytes32 commitment)
        external view returns (address currentOwner, uint256 timestamp)
    {
        Record memory r = records[creator][commitment];
        require(r.timestamp != 0, "Not found");
        return (r.currentOwner, r.timestamp);
    }

    // The claimed creator's address is part of the hash, so a copied hash
    // registered by someone else can never verify as theirs.
    // Must match Python: keccak256(abi.encodePacked(address, uint256[], bytes32)).
    function verifyReveal(address creator, uint256[] calldata vector, bytes32 salt)
        external view returns (bool, address, uint256)
    {
        bytes32 commitment = keccak256(abi.encodePacked(creator, vector, salt));
        Record memory r = records[creator][commitment];
        if (r.timestamp == 0) {
            return (false, address(0), 0);
        }
        return (true, r.currentOwner, r.timestamp);
    }

    // Only the creator, and only while they still hold it, can hand it over.
    function transferOwnership(bytes32 commitment, address newOwner) external {
        Record storage r = records[msg.sender][commitment];
        require(r.timestamp != 0 && r.currentOwner == msg.sender, "Not the owner");
        require(newOwner != address(0), "Zero address");
        r.currentOwner = newOwner;
        emit OwnershipTransferred(commitment, msg.sender, newOwner);
    }
}