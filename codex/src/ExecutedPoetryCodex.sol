// SPDX-License-Identifier: WTFPL
pragma solidity ^0.8.30;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/common/ERC2981.sol";
import "@openzeppelin/contracts/utils/Base64.sol";

interface IRenderer {
    function renderImage(uint256 tokenId, string[] memory files, string[] memory fileContents, uint256 defaultFileIndex) external view returns (string memory);
    function renderThumbnail(uint256 tokenId, string[] memory files, string[] memory fileContents, uint256 defaultFileIndex) external view returns (string memory);
}

contract ExecutedPoetryCodex is ERC721, ERC2981, Ownable {
    uint256 private constant MAIN_PY_INDEX = 10;

    IRenderer public renderer;
    address public minter;
    uint256 public constant MAX_SUPPLY = 6;
    uint256 public totalSupply;
    
    mapping(uint256 => uint256) public defaultFileIndexes;
    mapping(uint256 => string) public tokenNames;
    
    string[] public fileNames;
    string[] public baseFileContents;

    event Mint(address indexed to, uint256 indexed tokenId);

    constructor(address _owner, address _renderer, address _royaltyReceiver) ERC721("Executed Poetry Codex", "CODEX") Ownable(_owner) {
        renderer = IRenderer(_renderer);
        minter = _owner;
        _setDefaultRoyalty(_royaltyReceiver, 1000);
        
        fileNames = [
            "1.py",
            "2.py",
            "3.py",
            "4.py",
            "5.py",
            "6.py",
            "7.py",
            "8.py",
            "9.py",
            "10.py",
            "main.py",
            "ed25519.py"
        ];
        
        defaultFileIndexes[1] = 0;
        defaultFileIndexes[2] = 3;
        defaultFileIndexes[3] = 4;
        defaultFileIndexes[4] = 5;
        defaultFileIndexes[5] = 6;
        defaultFileIndexes[6] = 9;
        
        tokenNames[1] = "Count the mornings. One for each window. Until light is born.";
        tokenNames[2] = "Make a box for remembering you. Each time you look inside, I become you.";
        tokenNames[3] = "Touch eternity, and immediately let go.";
        tokenNames[4] = "Draw the outline of \\\"nothing\\\". Do not try to fill it.";
        tokenNames[5] = "Whisper to a mirror that you are not there. Until it fogs over.";
        tokenNames[6] = "If your heart is empty, borrow love from the universe.";
    }

    function setMinter(address m) external onlyOwner {
        minter = m;
    }

    function setRenderer(address r) external onlyOwner {
        renderer = IRenderer(r);
    }

    function setDefaultRoyalty(address receiver, uint96 bps) external onlyOwner {
        _setDefaultRoyalty(receiver, bps);
    }

    function setFileContents(string[] memory contents) external onlyOwner {
        require(contents.length == fileNames.length, "invalid length");
        baseFileContents = contents;
    }

    function _replaceMainPy(string memory mainPyContent, uint256 defaultIdx) internal pure returns (string memory) {
        bytes memory content = bytes(mainPyContent);
        bytes memory defaultIdxBytes = bytes(_toString(defaultIdx));
        bytes memory newDefaultIdx = abi.encodePacked("DEFAULT_IDX = ", defaultIdxBytes);
        
        return string(_replaceBytes(content, "DEFAULT_IDX = 1", newDefaultIdx));
    }

    function _replaceBytes(bytes memory data, string memory search, bytes memory replace) internal pure returns (bytes memory) {
        bytes memory searchBytes = bytes(search);
        if (searchBytes.length == 0) return data;
        if (searchBytes.length > data.length) return data;
        
        uint256 count = 0;
        uint256[] memory positions = new uint256[](data.length / searchBytes.length);
        
        for (uint256 i = 0; i <= data.length - searchBytes.length; i++) {
            bool found = true;
            for (uint256 j = 0; j < searchBytes.length; j++) {
                if (data[i + j] != searchBytes[j]) {
                    found = false;
                    break;
                }
            }
            if (found) {
                positions[count] = i;
                count++;
                i += searchBytes.length - 1;
            }
        }
        
        if (count == 0) return data;
        
        unchecked {
            uint256 diff = replace.length > searchBytes.length 
                ? replace.length - searchBytes.length 
                : searchBytes.length - replace.length;
            uint256 lengthDiff = diff * count;
            uint256 resultLength = replace.length > searchBytes.length
                ? data.length + lengthDiff
                : data.length - lengthDiff;
            bytes memory result = new bytes(resultLength);
            
            uint256 resultIndex = 0;
            uint256 posIndex = 0;
            
            for (uint256 i = 0; i < data.length; i++) {
                if (posIndex < count && i == positions[posIndex]) {
                    for (uint256 j = 0; j < replace.length; j++) {
                        result[resultIndex++] = replace[j];
                    }
                    i += searchBytes.length - 1;
                    posIndex++;
                } else {
                    result[resultIndex++] = data[i];
                }
            }
            
            return result;
        }
    }

    function _getFileContentsForToken(uint256 tokenId) internal view returns (string[] memory) {
        string[] memory contents = new string[](baseFileContents.length);
        for (uint256 i = 0; i < baseFileContents.length; i++) {
            if (i == MAIN_PY_INDEX) {
                uint256 defaultIdx = defaultFileIndexes[tokenId] + 1;
                contents[i] = _replaceMainPy(baseFileContents[i], defaultIdx);
            } else {
                contents[i] = baseFileContents[i];
            }
        }
        return contents;
    }

    function mint(address to, uint256 tokenId) public {
        require(msg.sender == minter, "not minter");
        require(tokenId >= 1 && tokenId <= MAX_SUPPLY, "invalid tokenId");
        require(_ownerOf(tokenId) == address(0), "already minted");
        require(totalSupply < MAX_SUPPLY, "max supply reached");
        
        _mint(to, tokenId);
        totalSupply++;
        emit Mint(to, tokenId);
    }

    function mintBatch(address[] memory to, uint256[] memory tokenIds) public {
        require(msg.sender == minter, "not minter");
        require(to.length == tokenIds.length, "length mismatch");
        
        for (uint256 i = 0; i < to.length; i++) {
            mint(to[i], tokenIds[i]);
        }
    }

    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        require(_ownerOf(tokenId) != address(0), "token does not exist");
        require(baseFileContents.length == fileNames.length, "file contents not set");
        
        uint256 defaultIndex = defaultFileIndexes[tokenId];
        string[] memory tokenFileContents = _getFileContentsForToken(tokenId);
        
        string memory thumbnail = IRenderer(renderer).renderThumbnail(
            tokenId,
            fileNames,
            tokenFileContents,
            defaultIndex
        );
        
        string memory animation = IRenderer(renderer).renderImage(
            tokenId,
            fileNames,
            tokenFileContents,
            defaultIndex
        );

        string memory json = string.concat(
            '{',
                '"name":"', tokenNames[tokenId], '",',
                '"description":"Executed Poetry Codex is a smart contract designed to preserve the source code of the code poetry work \\"Executed Poetry\\". It serves as a commemorative token gifted to the owner of the physical device.",',
                '"image":"', thumbnail, '",',
                '"animation_url":"', animation, '",',
                '"author":"Zeroichi Arakawa",',
                '"license":"WTFPL"',
            '}'
        );

        return string.concat("data:application/json;base64,", Base64.encode(bytes(json)));
    }

    function supportsInterface(bytes4 interfaceId) public view override(ERC721, ERC2981) returns (bool) {
        return super.supportsInterface(interfaceId);
    }

    function _toString(uint256 value) internal pure returns (string memory str) {
        if (value == 0) return "0";
        uint256 temp = value;
        uint256 digits;
        while (temp != 0) {
            digits++;
            temp /= 10;
        }
        bytes memory buffer = new bytes(digits);
        while (value != 0) {
            digits -= 1;
            buffer[digits] = bytes1(uint8(48 + uint256(value % 10)));
            value /= 10;
        }
        str = string(buffer);
    }
}

