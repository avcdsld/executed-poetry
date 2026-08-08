// SPDX-License-Identifier: WTFPL
pragma solidity ^0.8.30;

import "solady/src/utils/LibString.sol";
import "@openzeppelin/contracts/utils/Base64.sol";

contract ExecutedPoetryRenderer {
    function renderImage(uint256 tokenId, string[] memory files, string[] memory fileContents, uint256 defaultFileIndex) external pure returns (string memory) {
        string memory html = _generateEditorHtml(tokenId, files, fileContents, defaultFileIndex);
        return string.concat("data:text/html;charset=utf-8;base64,", Base64.encode(bytes(html)));
    }

    function renderThumbnail(uint256 tokenId, string[] memory files, string[] memory fileContents, uint256 defaultFileIndex) external pure returns (string memory) {
        string memory svg = _generateThumbnailSvg(tokenId, files, fileContents, defaultFileIndex);
        return string.concat("data:image/svg+xml;base64,", Base64.encode(bytes(svg)));
    }

    function _generateEditorHtml(uint256 tokenId, string[] memory files, string[] memory fileContents, uint256 defaultFileIndex) internal pure returns (string memory) {
        string memory fileListHtml = _generateFileListHtml(files, defaultFileIndex);
        
        return string.concat(
            "<!DOCTYPE html>",
            "<html lang=\"en\">",
            "<head>",
            "<meta charset=\"UTF-8\">",
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">",
            "<title>Executed Poetry #", _toString(tokenId), "</title>",
            "<style>",
            "* { margin: 0; padding: 0; box-sizing: border-box; }",
            "html, body { width: 100%; height: 100%; margin: 0; padding: 0; }",
            "body { font-family: 'Monaco', 'Menlo', 'Courier New', monospace; font-size: 12px; line-height: 1.4; color: #e0e0e0; background: #1e1e1e; display: flex; height: 100vh; overflow: hidden; }",
            ".file-list { width: 120px; min-width: 120px; max-width: 120px; background: #252526; border-right: 1px solid #3e3e42; overflow-y: auto; overflow-x: hidden; padding: 6px 0; flex-shrink: 0; }",
            ".file-list::-webkit-scrollbar { width: 4px; }",
            ".file-list::-webkit-scrollbar-track { background: #252526; }",
            ".file-list::-webkit-scrollbar-thumb { background: #3e3e42; border-radius: 2px; }",
            ".file-list::-webkit-scrollbar-thumb:hover { background: #4e4e52; }",
            ".file-item { padding: 4px 8px; cursor: pointer; color: #cccccc; transition: background 0.15s; font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }",
            ".file-item:hover { background: #2a2d2e; }",
            ".file-item.active { background: #094771; color: #ffffff; }",
            ".editor { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; }",
            ".editor-header { background: #2d2d30; padding: 6px 12px; border-bottom: 1px solid #3e3e42; color: #cccccc; font-size: 11px; flex-shrink: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }",
            ".editor-content { flex: 1; overflow: auto; padding: 12px; white-space: pre; color: #d4d4d4; font-size: 12px; }",
            ".editor-content::-webkit-scrollbar { width: 6px; height: 6px; }",
            ".editor-content::-webkit-scrollbar-track { background: #1e1e1e; }",
            ".editor-content::-webkit-scrollbar-thumb { background: #3e3e42; border-radius: 3px; }",
            ".editor-content::-webkit-scrollbar-thumb:hover { background: #4e4e52; }",
            ".line-number { color: #858585; margin-right: 12px; user-select: none; display: inline-block; min-width: 32px; text-align: right; font-size: 11px; }",
            ".code-line { display: flex; min-height: 1.4em; }",
            "@media (max-width: 800px) {",
            "  .file-list { width: 100px; min-width: 100px; max-width: 100px; }",
            "  .file-item { font-size: 10px; padding: 3px 6px; }",
            "  .editor-header { padding: 5px 10px; font-size: 10px; }",
            "  .editor-content { padding: 10px; font-size: 11px; }",
            "  .line-number { margin-right: 10px; min-width: 28px; font-size: 10px; }",
            "}",
            "@media (max-width: 500px) {",
            "  .file-list { width: 90px; min-width: 90px; max-width: 90px; }",
            "  .file-item { font-size: 9px; padding: 3px 4px; }",
            "  .editor-header { padding: 4px 8px; font-size: 9px; }",
            "  .editor-content { padding: 8px; font-size: 10px; }",
            "  .line-number { margin-right: 8px; min-width: 24px; font-size: 9px; }",
            "}",
            "@media (max-width: 400px) {",
            "  .file-list { width: 80px; min-width: 80px; max-width: 80px; }",
            "  .file-item { font-size: 8px; padding: 2px 4px; }",
            "  .editor-header { padding: 3px 6px; font-size: 8px; }",
            "  .editor-content { padding: 6px; font-size: 9px; }",
            "  .line-number { margin-right: 6px; min-width: 20px; font-size: 8px; }",
            "}",
            "</style>",
            "</head>",
            "<body>",
            "<div class=\"file-list\">",
            fileListHtml,
            "</div>",
            "<div class=\"editor\">",
            "<div class=\"editor-header\">",
            "<span id=\"current-file\">", files[defaultFileIndex], "</span>",
            "</div>",
            "<div class=\"editor-content\" id=\"editor-content\"></div>",
            "</div>",
            "<script>",
            "const files = [", _formatFileArray(files), "];",
            "const fileContents = [", _formatFileContentsArray(fileContents), "];",
            "let currentIndex = ", _toString(defaultFileIndex), ";",
            "const fileItems = document.querySelectorAll('.file-item');",
            "const editorContent = document.getElementById('editor-content');",
            "const currentFileSpan = document.getElementById('current-file');",
            "function formatCodeWithLineNumbers(code) {",
            "  const lines = code.split('\\n');",
            "  return lines.map((line, i) => {",
            "    const escaped = escapeHtml(line || ' ');",
            "    return '<div class=\"code-line\"><span class=\"line-number\">' + (i + 1) + '</span><span>' + escaped + '</span></div>';",
            "  }).join('');",
            "}",
            "function escapeHtml(text) {",
            "  const div = document.createElement('div');",
            "  div.textContent = text;",
            "  return div.innerHTML;",
            "}",
            "editorContent.innerHTML = formatCodeWithLineNumbers(fileContents[currentIndex]);",
            "fileItems.forEach((item, index) => {",
            "  item.addEventListener('click', () => {",
            "    fileItems.forEach(i => i.classList.remove('active'));",
            "    item.classList.add('active');",
            "    currentIndex = index;",
            "    currentFileSpan.textContent = files[index];",
            "    editorContent.innerHTML = formatCodeWithLineNumbers(fileContents[index]);",
            "  });",
            "});",
            "</script>",
            "</body>",
            "</html>"
        );
    }

    function _generateFileListHtml(string[] memory files, uint256 defaultIndex) internal pure returns (string memory) {
        string memory result = "";
        for (uint256 i = 0; i < files.length; i++) {
            string memory activeClass = i == defaultIndex ? " active" : "";
            result = string.concat(
                result,
                "<div class=\"file-item", activeClass, "\" data-index=\"", _toString(i), "\">",
                _escapeHtml(files[i]),
                "</div>"
            );
        }
        return result;
    }

    function _extractLine(bytes memory data, uint256 start, uint256 length) internal pure returns (string memory) {
        if (length == 0) return " ";
        bytes memory line = new bytes(length);
        for (uint256 i = 0; i < length; i++) {
            line[i] = data[start + i];
        }
        return string(line);
    }

    function _formatFileArray(string[] memory files) internal pure returns (string memory) {
        string memory result = "";
        for (uint256 i = 0; i < files.length; i++) {
            if (i > 0) result = string.concat(result, ",");
            string memory escaped = _escapeJsString(files[i]);
            result = string.concat(result, "\"", escaped, "\"");
        }
        return result;
    }

    function _formatFileContentsArray(string[] memory contents) internal pure returns (string memory) {
        string memory result = "";
        for (uint256 i = 0; i < contents.length; i++) {
            if (i > 0) result = string.concat(result, ",");
            string memory escaped = _escapeJsString(contents[i]);
            result = string.concat(result, "\"", escaped, "\"");
        }
        return result;
    }

    function _escapeJsString(string memory input) internal pure returns (string memory) {
        bytes memory inputBytes = bytes(input);
        bytes memory output = new bytes(inputBytes.length * 2);
        uint256 outputIndex = 0;
        
        for (uint256 i = 0; i < inputBytes.length; i++) {
            bytes1 char = inputBytes[i];
            
            if (char == 0x22) {
                output[outputIndex++] = 0x5C;
                output[outputIndex++] = 0x22;
            } else if (char == 0x5C) {
                output[outputIndex++] = 0x5C;
                output[outputIndex++] = 0x5C;
            } else if (char == 0x0A) {
                output[outputIndex++] = 0x5C;
                output[outputIndex++] = 0x6E;
            } else if (char == 0x0D) {
                output[outputIndex++] = 0x5C;
                output[outputIndex++] = 0x72;
            } else if (char == 0x09) {
                output[outputIndex++] = 0x5C;
                output[outputIndex++] = 0x74;
            } else {
                output[outputIndex++] = char;
            }
        }
        
        bytes memory resultBytes = new bytes(outputIndex);
        for (uint256 i = 0; i < outputIndex; i++) {
            resultBytes[i] = output[i];
        }
        return string(resultBytes);
    }

    function _escapeHtml(string memory input) internal pure returns (string memory) {
        string memory result = LibString.replace(input, "&", "&amp;");
        result = LibString.replace(result, "<", "&lt;");
        result = LibString.replace(result, ">", "&gt;");
        result = LibString.replace(result, "\"", "&quot;");
        result = LibString.replace(result, "'", "&#39;");
        return result;
    }

    function _generateThumbnailSvg(uint256 /* tokenId */, string[] memory files, string[] memory fileContents, uint256 defaultFileIndex) internal pure returns (string memory) {
        string memory fileName = files[defaultFileIndex];
        string memory code = fileContents[defaultFileIndex];
        string memory codeLines = _generateCodeLinesSvg(code, 20);
        
        return string.concat(
            "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"512\" height=\"512\"><rect width=\"512\" height=\"512\" fill=\"#1e1e1e\"/><rect x=\"0\" y=\"0\" width=\"120\" height=\"512\" fill=\"#252526\"/>",
            _generateFileListSvgMinimal(files, defaultFileIndex),
            "<rect x=\"120\" y=\"0\" width=\"392\" height=\"512\" fill=\"#1e1e1e\"/><rect x=\"120\" y=\"0\" width=\"392\" height=\"30\" fill=\"#2d2d30\"/>",
            "<text x=\"130\" y=\"20\" font-family=\"monospace\" font-size=\"11\" fill=\"#ccc\">", _escapeSvgMinimal(fileName), "</text>",
            codeLines,
            "</svg>"
        );
    }

    function _generateCodeLinesSvg(string memory code, uint256 maxLines) internal pure returns (string memory) {
        bytes memory codeBytes = bytes(code);
        string memory result = "";
        uint256 lineCount = 0;
        uint256 y = 50;
        uint256 startIndex = 0;
        
        for (uint256 i = 0; i < codeBytes.length && lineCount < maxLines; i++) {
            if (codeBytes[i] == 0x0A) {
                uint256 lineLength = i - startIndex;
                string memory line = _extractLine(codeBytes, startIndex, lineLength);
                result = string.concat(
                    result,
                    "<text x=\"130\" y=\"", _toString(y), "\" font-family=\"monospace\" font-size=\"11\" fill=\"#d4d4d4\" xml:space=\"preserve\">", _escapeSvgWithSpaces(line), "</text>"
                );
                y += 16;
                lineCount++;
                startIndex = i + 1;
            }
        }
        
        if (lineCount < maxLines && startIndex < codeBytes.length) {
            uint256 lastLineLength = codeBytes.length - startIndex;
            string memory lastLine = _extractLine(codeBytes, startIndex, lastLineLength);
            result = string.concat(
                result,
                "<text x=\"130\" y=\"", _toString(y), "\" font-family=\"monospace\" font-size=\"11\" fill=\"#d4d4d4\" xml:space=\"preserve\">", _escapeSvgWithSpaces(lastLine), "</text>"
            );
        }
        
        return result;
    }

    function _escapeSvgWithSpaces(string memory input) internal pure returns (string memory) {
        bytes memory inputBytes = bytes(input);
        bytes memory output = new bytes(inputBytes.length * 6);
        uint256 outputIndex = 0;
        
        for (uint256 i = 0; i < inputBytes.length; i++) {
            bytes1 char = inputBytes[i];
            if (char == 0x3c) {
                output[outputIndex++] = 0x26;
                output[outputIndex++] = 0x6c;
                output[outputIndex++] = 0x74;
                output[outputIndex++] = 0x3b;
            } else if (char == 0x3e) {
                output[outputIndex++] = 0x26;
                output[outputIndex++] = 0x67;
                output[outputIndex++] = 0x74;
                output[outputIndex++] = 0x3b;
            } else if (char == 0x26) {
                output[outputIndex++] = 0x26;
                output[outputIndex++] = 0x61;
                output[outputIndex++] = 0x6d;
                output[outputIndex++] = 0x70;
                output[outputIndex++] = 0x3b;
            } else if (char == 0x20) {
                output[outputIndex++] = 0x26;
                output[outputIndex++] = 0x23;
                output[outputIndex++] = 0x31;
                output[outputIndex++] = 0x36;
                output[outputIndex++] = 0x30;
                output[outputIndex++] = 0x3b;
            } else {
                output[outputIndex++] = char;
            }
        }
        
        bytes memory resultBytes = new bytes(outputIndex);
        for (uint256 i = 0; i < outputIndex; i++) {
            resultBytes[i] = output[i];
        }
        return string(resultBytes);
    }

    function _generateFileListSvgMinimal(string[] memory files, uint256 defaultFileIndex) internal pure returns (string memory) {
        string memory result = "";
        string[12] memory yPositions = ["8", "28", "48", "68", "88", "108", "128", "148", "168", "188", "208", "228"];
        string[12] memory yTexts = ["20", "40", "60", "80", "100", "120", "140", "160", "180", "200", "220", "240"];
        
        for (uint256 i = 0; i < files.length && i < 12; i++) {
            string memory fill = i == defaultFileIndex ? "#094771" : "#252526";
            string memory color = i == defaultFileIndex ? "#fff" : "#ccc";
            result = string.concat(
                result,
                "<rect x=\"0\" y=\"", yPositions[i], "\" width=\"120\" height=\"20\" fill=\"", fill, "\"/>",
                "<text x=\"8\" y=\"", yTexts[i], "\" font-family=\"monospace\" font-size=\"11\" fill=\"", color, "\">", _escapeSvgMinimal(files[i]), "</text>"
            );
        }
        return result;
    }

    function _escapeSvgMinimal(string memory input) internal pure returns (string memory) {
        bytes memory inputBytes = bytes(input);
        bytes memory output = new bytes(inputBytes.length * 6);
        uint256 outputIndex = 0;
        
        for (uint256 i = 0; i < inputBytes.length; i++) {
            bytes1 char = inputBytes[i];
            if (char == 0x3c) {
                output[outputIndex++] = 0x26;
                output[outputIndex++] = 0x6c;
                output[outputIndex++] = 0x74;
                output[outputIndex++] = 0x3b;
            } else if (char == 0x3e) {
                output[outputIndex++] = 0x26;
                output[outputIndex++] = 0x67;
                output[outputIndex++] = 0x74;
                output[outputIndex++] = 0x3b;
            } else if (char == 0x26) {
                output[outputIndex++] = 0x26;
                output[outputIndex++] = 0x61;
                output[outputIndex++] = 0x6d;
                output[outputIndex++] = 0x70;
                output[outputIndex++] = 0x3b;
            } else {
                output[outputIndex++] = char;
            }
        }
        
        bytes memory resultBytes = new bytes(outputIndex);
        for (uint256 i = 0; i < outputIndex; i++) {
            resultBytes[i] = output[i];
        }
        return string(resultBytes);
    }



    function _generateFileListSvg(string[] memory files, uint256 defaultFileIndex) internal pure returns (string memory) {
        string memory result = "";
        uint256 y = 20;
        for (uint256 i = 0; i < files.length; i++) {
            string memory fillColor = i == defaultFileIndex ? "#094771" : "#252526";
            string memory textColor = i == defaultFileIndex ? "#ffffff" : "#cccccc";
            result = string.concat(
                result,
                "<rect x=\"0\" y=\"", _toString(y - 12), "\" width=\"120\" height=\"20\" fill=\"", fillColor, "\"/>",
                "<text x=\"8\" y=\"", _toString(y), "\" font-family=\"Monaco, Menlo, monospace\" font-size=\"11\" fill=\"", textColor, "\">", _escapeSvg(files[i]), "</text>"
            );
            y += 20;
        }
        return result;
    }

    function _truncateCode(string memory code, uint256 maxLines) internal pure returns (string memory) {
        bytes memory codeBytes = bytes(code);
        uint256 lineCount = 0;
        uint256 endIndex = codeBytes.length;
        
        for (uint256 i = 0; i < codeBytes.length && lineCount < maxLines; i++) {
            if (codeBytes[i] == 0x0A) {
                lineCount++;
                if (lineCount >= maxLines) {
                    endIndex = i;
                    break;
                }
            }
        }
        
        if (endIndex < codeBytes.length) {
            bytes memory truncated = new bytes(endIndex);
            for (uint256 i = 0; i < endIndex; i++) {
                truncated[i] = codeBytes[i];
            }
            return string(truncated);
        }
        return code;
    }

    function _escapeSvg(string memory input) internal pure returns (string memory) {
        string memory result = LibString.replace(input, "&", "&amp;");
        result = LibString.replace(result, "<", "&lt;");
        result = LibString.replace(result, ">", "&gt;");
        result = LibString.replace(result, "\"", "&quot;");
        result = LibString.replace(result, "'", "&#39;");
        return result;
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
