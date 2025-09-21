# StockTrading.py - 개선된 파일 저장/로드 기능이 있는 웹서버

import http.server
import socketserver
import webbrowser
import os
import sys
import json
import urllib.parse
from pathlib import Path
from datetime import datetime
import yfinance as yf # yfinance 라이브러리 추가

class StockDataHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        """POST 요청 처리 (데이터 저장/로드)"""
        if self.path == '/api/save':
            self.save_data()
        elif self.path == '/api/load':
            self.load_data()
        elif self.path == '/api/load_file':  # 새로운 엔드포인트: 임의의 파일 로드
            self.load_file_from_path()
        elif self.path == '/api/update_prices': # 주식 가격 업데이트
            self.update_prices()
        elif self.path == '/api/update_exchange_rate': # 환율 자동 업데이트 추가
            self.update_exchange_rate()
        else:
            self.send_error(404)
    
    def do_GET(self):
        """GET 요청 처리"""
        if self.path == '/api/files':
            self.list_files()
        else:
            super().do_GET()
    
    def update_prices(self):
        """'종목 코드'를 사용하여 현재가 업데이트"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            stock_codes = request_data.get('stock_codes', [])
            exchange_rate = request_data.get('exchange_rate', 1)

            updated_stocks = {}
            for code in stock_codes:
                try:
                    # yfinance를 사용하여 현재가 가져오기
                    ticker = yf.Ticker(code)
                    current_price = ticker.info.get('currentPrice')
                    if current_price:
                        # 미국 주식인 경우 환율을 곱하여 원화로 변환
                        if not code.endswith('.KS') and not code.endswith('.KQ'):
                            current_price = int(current_price * exchange_rate)
                        
                        updated_stocks[code] = current_price
                    else:
                        updated_stocks[code] = None # 가격 정보를 찾을 수 없는 경우
                except Exception as e:
                    print(f"⌛ 종목 코드 {code}의 가격 업데이트 중 오류 발생: {e}")
                    updated_stocks[code] = None

            response = {"success": True, "updated_prices": updated_stocks}
            self.send_json_response(response)
            
        except Exception as e:
            error_response = {"success": False, "error": str(e)}
            self.send_json_response(error_response, 500)

    def update_exchange_rate(self):
        """실시간 환율(USD→KRW) 업데이트"""
        try:
            ticker = yf.Ticker("USDKRW=X")
            exchange_rate = ticker.info.get("regularMarketPrice")

            if exchange_rate:
                response = {"success": True, "exchange_rate": round(exchange_rate, 2)}
            else:
                response = {"success": False, "error": "환율 정보를 가져올 수 없습니다."}

            self.send_json_response(response)

        except Exception as e:
            error_response = {"success": False, "error": str(e)}
            self.send_json_response(error_response, 500)

    def save_data(self):
        """데이터를 JSON 파일로 저장 (사용자 정의 파일명 지원)"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            data = request_data.get('data', [])
            custom_filename = request_data.get('filename', '')
            save_path = request_data.get('save_path', '')
            
            # 파일명 처리
            if custom_filename:
                if not custom_filename.endswith('.json'):
                    custom_filename += '.json'
                filename = custom_filename
            else:
                # 기본 타임스탬프 파일명
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"stock_data_{timestamp}.json"
            
            # 저장 경로 결정
            if save_path:
                # 사용자가 지정한 경로
                save_dir = Path(save_path)
                if not save_dir.exists():
                    save_dir.mkdir(parents=True, exist_ok=True)
            else:
                # 기본 경로
                save_dir = Path("stock_data")
                save_dir.mkdir(exist_ok=True)
            
            # 파일 저장
            file_path = save_dir / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 응답
            response = {"success": True, "filename": filename, "path": str(file_path.absolute())}
            self.send_json_response(response)
            
        except Exception as e:
            error_response = {"success": False, "error": str(e)}
            self.send_json_response(error_response, 500)
    
    def load_data(self):
        """기본 stock_data 폴더에서 JSON 파일 로드"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            filename = request_data.get('filename')
            if not filename:
                raise ValueError("파일명이 필요합니다.")
            
            file_path = Path("stock_data") / filename
            
            if not file_path.exists():
                raise FileNotFoundError(f"파일을 찾을 수 없습니다: {filename}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            response = {"success": True, "data": data, "filename": filename}
            self.send_json_response(response)
            
        except Exception as e:
            error_response = {"success": False, "error": str(e)}
            self.send_json_response(error_response, 500)
    
    def load_file_from_path(self):
        """임의의 경로에서 JSON 파일 로드"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            file_path = request_data.get('file_path')
            if not file_path:
                raise ValueError("파일 경로가 필요합니다.")
            
            file_path = Path(file_path)
            
            if not file_path.exists():
                raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
            
            if not file_path.suffix.lower() == '.json':
                raise ValueError("JSON 파일만 지원됩니다.")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            response = {"success": True, "data": data, "filename": file_path.name, "path": str(file_path.absolute())}
            self.send_json_response(response)
            
        except Exception as e:
            error_response = {"success": False, "error": str(e)}
            self.send_json_response(error_response, 500)
    
    def list_files(self):
        """저장된 파일 목록 반환"""
        try:
            data_dir = Path("stock_data")
            files = []
            
            if data_dir.exists():
                for file_path in data_dir.glob("*.json"):
                    stat = file_path.stat()
                    files.append({
                        "filename": file_path.name,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                        "path": str(file_path.absolute())
                    })
            
            # 최신 파일부터 정렬
            files.sort(key=lambda x: x['modified'], reverse=True)
            
            response = {"success": True, "files": files}
            self.send_json_response(response)
            
        except Exception as e:
            error_response = {"success": False, "error": str(e)}
            self.send_json_response(error_response, 500)
    
    def send_json_response(self, data, status_code=200):
        """JSON 응답 전송"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
        response_json = json.dumps(data, ensure_ascii=False)
        self.wfile.write(response_json.encode('utf-8'))

def create_html_file():
    """HTML 파일 생성"""
    html_content = '''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>주식 매매 관리 시스템</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f5f5;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            padding: 30px;
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #e5e5e5;
            padding-bottom: 20px;
            flex-wrap: wrap;
        }

        .header-controls {
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
        }

        h1 {
            color: #333;
            font-size: 2.5rem;
            font-weight: bold;
        }

        .btn {
            padding: 10px 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.3s;
            white-space: nowrap;
        }

        .add-btn {
            background: #007bff;
            color: white;
        }

        .add-btn:hover {
            background: #0056b3;
        }

        .auto-update-btn {
            background: #28a745;
            color: white;
        }

        .auto-update-btn:hover {
            background: #1e7e34;
        }

        .auto-update-btn:disabled {
            background: #6c757d;
            cursor: not-allowed;
        }
        
        .delete-all-btn {
            background: #dc3545;
            color: white;
        }

        .delete-all-btn:hover {
            background: #c82333;
        }

        .save-btn {
            background: #17a2b8;
            color: white;
        }

        .save-btn:hover {
            background: #138496;
        }

        .load-btn {
            background: #ffc107;
            color: #212529;
        }

        .load-btn:hover {
            background: #e0a800;
        }

        .form-section {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            border: 1px solid #dee2e6;
        }

        .form-section.hidden {
            display: none;
        }

        .form-title {
            font-size: 1.2rem;
            font-weight: 600;
            margin-bottom: 15px;
            color: #495057;
        }

        .form-row {
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
            margin-bottom: 15px;
        }

        .form-input {
            flex: 1;
            padding: 10px 12px;
            border: 1px solid #ced4da;
            border-radius: 5px;
            font-size: 16px;
            min-width: 200px;
        }

        .form-input:focus {
            outline: none;
            border-color: #007bff;
            box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
        }

        .form-input-small {
            min-width: 150px;
            flex: 0 0 150px;
        }

        select {
            padding: 10px 12px;
            border: 1px solid #ced4da;
            border-radius: 5px;
            font-size: 14px;
            background: white;
            min-width: 200px;
        }

        .btn-success {
            background: #28a745;
            color: white;
        }

        .btn-success:hover {
            background: #1e7e34;
        }

        .btn-secondary {
            background: #6c757d;
            color: white;
        }

        .btn-secondary:hover {
            background: #545b62;
        }

        .btn-danger {
            background: #dc3545;
            color: white;
        }

        .btn-danger:hover {
            background: #c82333;
        }

        .btn-primary {
            background: #007bff;
            color: white;
        }

        .btn-primary:hover {
            background: #0056b3;
        }
        
        .settings-btn {
            background: #6f42c1;
            color: white;
        }
        
        .settings-btn:hover {
            background: #5a3a99;
        }
        
        .settings-info {
            font-size: 14px;
            color: #6c757d;
            margin: 0 10px;
            white-space: nowrap;
        }

        .table-container {
            overflow-x: auto;
            margin-bottom: 30px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            min-width: 1000px;
        }

        th {
            background: #343a40;
            color: white;
            padding: 15px 10px;
            text-align: left;
            font-weight: 600;
            border: 1px solid #495057;
        }

        td {
            padding: 12px 10px;
            border: 1px solid #dee2e6;
            vertical-align: top;
        }

        tr:nth-child(even) {
            background: #f8f9fa;
        }

        tr:hover {
            background: #e9ecef;
        }

        .text-right {
            text-align: right;
        }

        .text-center {
            text-align: center;
        }

        .text-green {
            color: #28a745;
            font-weight: 600;
        }

        .text-red {
            color: #dc3545;
            font-weight: 600;
        }

        .text-blue {
            color: #007bff;
            font-weight: 600;
        }

        .text-orange {
            color: #fd7e14;
            font-weight: 600;
        }

        .text-purple {
            color: #6f42c1;
            font-weight: 600;
        }

        .text-gray {
            color: #6c757d;
            font-weight: 600;
        }

        .small-text {
            font-size: 12px;
            opacity: 0.8;
        }

        .update-form {
            display: flex;
            gap: 8px;
            align-items: center;
        }

        .update-input {
            width: 80px;
            padding: 5px 8px;
            border: 1px solid #ced4da;
            border-radius: 3px;
            text-align: right;
        }

        .price-info {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
        }

        .management-column {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 5px;
        }

        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #6c757d;
        }

        .empty-state h3 {
            font-size: 1.5rem;
            margin-bottom: 10px;
        }

        .help-section {
            background: #e3f2fd;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #2196f3;
        }

        .help-title {
            color: #1976d2;
            font-weight: 600;
            margin-bottom: 10px;
            font-size: 1.1rem;
        }

        .help-content {
            color: #1565c0;
            font-size: 14px;
            line-height: 1.6;
        }

        .help-item {
            margin-bottom: 5px;
        }

        .update-icon {
            cursor: pointer;
            color: #007bff;
            font-size: 14px;
            padding: 2px;
            border-radius: 3px;
            transition: background 0.3s;
            margin-left: 5px;
        }

        .update-icon:hover {
            background: #e9ecef;
        }

        .file-list {
            max-height: 300px;
            overflow-y: auto;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            background: white;
        }

        .file-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 15px;
            border-bottom: 1px solid #dee2e6;
            cursor: pointer;
        }

        .file-item:hover {
            background: #f8f9fa;
        }

        .file-item.selected {
            background: #e7f3ff;
            border-left: 4px solid #007bff;
        }

        .file-info {
            flex: 1;
        }

        .file-name {
            font-weight: 600;
            color: #495057;
        }

        .file-details {
            font-size: 12px;
            color: #6c757d;
            margin-top: 3px;
        }

        .status-message {
            padding: 10px 15px;
            border-radius: 5px;
            margin: 15px 0;
            font-weight: 600;
        }

        .status-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }

        .status-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .setting-group {
            display: flex;
            flex-direction: column;
            gap: 5px;
            margin-bottom: 15px;
        }

        .form-group {
            display: flex;
            flex-direction: column;
            gap: 5px;
            margin-bottom: 15px;
        }

        .form-group label {
            font-weight: 600;
            color: #495057;
        }

        .path-display {
            font-size: 12px;
            color: #6c757d;
            padding: 5px 0;
            word-break: break-all;
        }

        .load-options {
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
            align-items: center;
        }

        .load-option {
            display: flex;
            align-items: center;
            gap: 5px;
        }

        .load-option input[type="radio"] {
            margin-right: 5px;
        }

        @media (max-width: 768px) {
            .header-controls {
                flex-direction: column;
                align-items: stretch;
            }
            
            .form-row {
                flex-direction: column;
                align-items: stretch;
            }
            
            .form-input {
                min-width: auto;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>주식 매매 관리 시스템</h1>
            <div class="header-controls">
                <button class="btn delete-all-btn" onclick="deleteAllStocks()">
                    🗑️ 전체 삭제
                </button>
                <button class="btn add-btn" onclick="toggleAddForm()">+ 주식 추가</button>
                <button class="btn settings-btn" onclick="toggleSettingsSection()">⚙️ 설정</button>
                <button class="btn auto-update-btn" onclick="updateAllPrices()">
                    🔄 현재가 업데이트
                </button>
                <button class="btn save-btn" onclick="toggleSaveSection()">💾 저장</button>
                <button class="btn load-btn" onclick="toggleLoadSection()">📂 불러오기</button>
            </div>
        </div>
        
        <div class="header-info">
            <span class="settings-info" id="currentSettings"></span>
        </div>

        <div id="saveSection" class="form-section hidden">
            <div class="form-title">💾 데이터 저장</div>
            <div class="form-group">
                <label for="saveFilename">파일명 (선택사항)</label>
                <input type="text" id="saveFilename" class="form-input" placeholder="예: 내_주식_포트폴리오 (확장자 .json은 자동 추가됩니다)" />
            </div>
            <div class="form-group">
                <label for="savePath">저장 경로 (선택사항)</label>
                <input type="text" id="savePath" class="form-input" placeholder="예: C:\\Users\\사용자명\\Documents (기본값: stock_data 폴더)" />
                <div class="path-display">기본 경로를 사용하려면 비워두세요. 절대 경로 또는 상대 경로를 입력할 수 있습니다.</div>
            </div>
            <div class="form-row">
                <button class="btn btn-success" onclick="saveDataToFile()">저장하기</button>
                <button class="btn btn-secondary" onclick="toggleSaveSection()">취소</button>
            </div>
        </div>

        <div id="loadSection" class="form-section hidden">
            <div class="form-title">📂 데이터 불러오기</div>
            
            <div class="load-options">
                <div class="load-option">
                    <input type="radio" id="loadFromDefault" name="loadOption" value="default" checked>
                    <label for="loadFromDefault">기본 폴더에서 선택</label>
                </div>
                <div class="load-option">
                    <input type="radio" id="loadFromCustom" name="loadOption" value="custom">
                    <label for="loadFromCustom">파일 경로 직접 입력</label>
                </div>
            </div>

            <div id="defaultLoadSection">
                <div style="margin-bottom: 15px;">
                    <p>저장된 파일 목록에서 불러올 파일을 선택하세요.</p>
                </div>
                <div class="file-list" id="fileList"></div>
                <div class="form-row" style="margin-top: 15px;">
                    <button class="btn btn-primary" onclick="loadSelectedFile()" id="loadBtn" disabled>선택한 파일 불러오기</button>
                    <button class="btn btn-secondary" onclick="refreshFileList()">목록 새로고침</button>
                </div>
            </div>

            <div id="customLoadSection" style="display: none;">
                <div class="form-group">
                    <label for="customFilePath">파일 경로</label>
                    <input type="text" id="customFilePath" class="form-input" placeholder="예: C:\\Users\\사용자명\\Documents\\내_주식_데이터.json" />
                    <div class="path-display">JSON 파일의 전체 경로를 입력하세요.</div>
                </div>
                <div class="form-row">
                    <button class="btn btn-primary" onclick="loadFromCustomPath()">파일 불러오기</button>
                </div>
            </div>

            <div class="form-row" style="margin-top: 15px;">
                <button class="btn btn-secondary" onclick="toggleLoadSection()">취소</button>
            </div>
        </div>
        
        <div id="settingsSection" class="form-section hidden">
            <div class="form-title">🔈 매매 설정 및 환율</div>
            <div class="setting-group">
                <label for="sellPercentageInput">매도 비율 (%)</label>
                <input type="number" id="sellPercentageInput" class="form-input" value="8" min="1" max="100" />
            </div>
            <div class="setting-group">
                <label for="buyMorePercentageInput">추가 매수 비율 (%)</label>
                <input type="number" id="buyMorePercentageInput" class="form-input" value="5" min="1" max="100" />
            </div>
            <div class="setting-group">
                <label for="exchangeRateInput">환율 (1 USD = ? KRW)</label>
               <div style="display: flex; gap: 10px; align-items: center;">
                   <input type="number" id="exchangeRateInput" class="form-input" value="1300" min="1" />
                   <button class="btn btn-primary" onclick="updateExchangeRate()">자동 업데이트</button>
               </div>
            </div>
            <button class="btn btn-secondary" onclick="toggleSettingsSection()">저장</button>
        </div>

        <div id="statusMessage" style="display: none;"></div>

        <div id="addForm" class="form-section hidden">
            <div class="form-title">새 주식 추가</div>
            <div class="form-row">
                <input type="text" id="stockName" class="form-input" placeholder="주식 이름" />
                <input type="text" id="stockCode" class="form-input" placeholder="종목 코드 (예: 005930.KS)" />
                <input type="number" id="purchasePrice" class="form-input" placeholder="매입가 (원화)" />
                <button class="btn btn-success" onclick="addStock()">추가</button>
                <button class="btn btn-secondary" onclick="toggleAddForm()">취소</button>
            </div>
        </div>

        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>주식 이름</th>
                        <th>종목 코드</th>
                        <th class="text-right">매입가</th>
                        <th class="text-right">현재가</th>
                        <th class="text-right">고점</th>
                        <th class="text-right">매도</th>
                        <th class="text-right">추가매수</th>
                        <th class="text-center">손익</th>
                        <th class="text-center">의견</th>
                        <th class="text-center">관리</th>
                    </tr>
                </thead>
                <tbody id="stockTableBody">
                </tbody>
            </table>
        </div>

        <div id="emptyState" class="empty-state">
            <h3>등록된 주식이 없습니다</h3>
            <p>주식을 추가하거나 저장된 파일을 불러와서 매매 관리를 시작하세요.</p>
        </div>

        <div class="help-section">
            <div class="help-title">사용 가이드</div>
            <div class="help-content">
                <div class="help-item"><strong>1. 매매 설정 및 환율</strong>: ⚙️ 설정 버튼을 눌러 매도 및 추가 매수 비율을 설정할 수 있고, 미국 주식 매매를 위해 환율을 설정할 수 있습니다.</div>
                <div class="help-item"><strong>2. 파일 저장</strong>: 💾 저장 버튼으로 현재 데이터를 .json 파일로 저장할 수 있습니다. 파일명과 저장 경로를 자유롭게 지정할 수 있습니다.</div>
                <div class="help-item"><strong>3. 파일 불러오기</strong>: 📂 불러오기 버튼으로 기본 폴더의 파일을 선택하거나, 임의의 경로에서 직접 파일을 불러올 수 있습니다.</div>
                <div class="help-item"><strong>4. 현재가 업데이트</strong>: "현재가 업데이트" 🔄 버튼으로 등록된 모든 종목의 현재가를 자동으로 업데이트합니다.</div>
                <div class="help-item"><strong>5. 수동 입력</strong>: 테이블의 현재가 옆 ✏️ 아이콘을 클릭하여 직접 가격을 입력할 수 있습니다.</div>
                <div class="help-item"><strong>6. 전체 삭제</strong>: "전체 삭제" 🗑️ 버튼으로 모든 주식 항목을 한번에 삭제할 수 있습니다.</div>
                <div class="help-item"><strong>7. 고점</strong>: 매입 후 현재가가 매입가보다 높을 때 업데이트됩니다.</div>
                <div class="help-item"><strong>8. 매도/추가매수</strong>: '설정'에서 지정한 비율에 따라 가격이 계산됩니다.</div>
                <div class="help-item"><strong>9. 의견</strong>: 현재가를 기준으로 매매 의견(매수, 매도, 유지)을 제공합니다.</div>
            </div>
        </div>
    </div>

    <script>
        let stocks = [];
        let editingId = null;
        let selectedFileName = null;
        let sellPercentage = 8;
        let buyMorePercentage = 5;
        let exchangeRate = 1300;

        // 환율 자동 업데이트
        async function updateExchangeRate() {
           try {
                const response = await fetch('/api/update_exchange_rate', { method: 'POST' });
                const result = await response.json();

                if (result.success) {
                    exchangeRate = result.exchange_rate;
                    document.getElementById('exchangeRateInput').value = exchangeRate;
                    updateSettings();
                    showStatus(`✅ 환율이 자동 업데이트되었습니다: 1 USD = ${exchangeRate} KRW`);
                } else {
                    showStatus(`⌛ 환율 업데이트 실패: ${result.error}`, true);
                }
            } catch (error) {
                showStatus(`⌛ 환율 업데이트 중 오류 발생: ${error.message}`, true);
            }
        }
        
        // 페이지 로드 시 실행
        document.addEventListener('DOMContentLoaded', function() {
            loadFromLocalStorage();
            loadSettings();
            
            document.getElementById('purchasePrice').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    addStock();
                }
            });
            
            document.getElementById('stockCode').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    document.getElementById('purchasePrice').focus();
                }
            });

            document.getElementById('stockName').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    document.getElementById('stockCode').focus();
                }
            });
            
            document.getElementById('sellPercentageInput').addEventListener('input', updateSettings);
            document.getElementById('buyMorePercentageInput').addEventListener('input', updateSettings);
            document.getElementById('exchangeRateInput').addEventListener('input', updateSettings);
            
            // 로드 옵션 변경 이벤트
            document.querySelectorAll('input[name="loadOption"]').forEach(radio => {
                radio.addEventListener('change', toggleLoadOption);
            });
        });
        
        // 로드 옵션 토글
        function toggleLoadOption() {
            const defaultSection = document.getElementById('defaultLoadSection');
            const customSection = document.getElementById('customLoadSection');
            const selectedOption = document.querySelector('input[name="loadOption"]:checked').value;
            
            if (selectedOption === 'default') {
                defaultSection.style.display = 'block';
                customSection.style.display = 'none';
                refreshFileList();
            } else {
                defaultSection.style.display = 'none';
                customSection.style.display = 'block';
            }
        }
        
        // 설정값 로드
        function loadSettings() {
            const savedSettings = localStorage.getItem('stockSettings');
            if (savedSettings) {
                const settings = JSON.parse(savedSettings);
                sellPercentage = settings.sellPercentage || 8;
                buyMorePercentage = settings.buyMorePercentage || 5;
                exchangeRate = settings.exchangeRate || 1300;
                
                document.getElementById('sellPercentageInput').value = sellPercentage;
                document.getElementById('buyMorePercentageInput').value = buyMorePercentage;
                document.getElementById('exchangeRateInput').value = exchangeRate;
            }
            updateSettingsDisplay();
        }
        
        // 설정값 업데이트
        function updateSettings() {
            sellPercentage = parseInt(document.getElementById('sellPercentageInput').value) || 8;
            buyMorePercentage = parseInt(document.getElementById('buyMorePercentageInput').value) || 5;
            exchangeRate = parseInt(document.getElementById('exchangeRateInput').value) || 1300;
            
            if (sellPercentage < 1 || sellPercentage > 100) sellPercentage = 8;
            if (buyMorePercentage < 1 || buyMorePercentage > 100) buyMorePercentage = 5;
            if (exchangeRate < 1) exchangeRate = 1300;

            const settings = { sellPercentage, buyMorePercentage, exchangeRate };
            localStorage.setItem('stockSettings', JSON.stringify(settings));
            
            updateSettingsDisplay();
            renderTable();
        }
        
        // 설정값 표시 업데이트
        function updateSettingsDisplay() {
            document.getElementById('currentSettings').textContent = 
                `매도 비율: ${sellPercentage}% | 추가 매수 비율: ${buyMorePercentage}% | 환율: 1 USD = ${exchangeRate.toLocaleString()} KRW`;
        }

        // 로컬 스토리지에서 데이터 로드
        function loadFromLocalStorage() {
            const savedStocks = localStorage.getItem('stockData');
            if (savedStocks) {
                stocks = JSON.parse(savedStocks);
                renderTable();
            }
        }

        // 로컬 스토리지에 데이터 저장
        function saveToLocalStorage() {
            localStorage.setItem('stockData', JSON.stringify(stocks));
        }

        // 상태 메시지 표시
        function showStatus(message, isError = false) {
            const statusDiv = document.getElementById('statusMessage');
            statusDiv.textContent = message;
            statusDiv.className = `status-message ${isError ? 'status-error' : 'status-success'}`;
            statusDiv.style.display = 'block';
            
            setTimeout(() => {
                statusDiv.style.display = 'none';
            }, 5000);
        }

        // 저장 섹션 토글
        function toggleSaveSection() {
            const section = document.getElementById('saveSection');
            section.classList.toggle('hidden');
            hideOtherSections('saveSection');
            
            if (!section.classList.contains('hidden')) {
                document.getElementById('saveFilename').focus();
            }
        }

        // 불러오기 섹션 토글
        function toggleLoadSection() {
            const section = document.getElementById('loadSection');
            section.classList.toggle('hidden');
            hideOtherSections('loadSection');
            
            if (!section.classList.contains('hidden')) {
                toggleLoadOption();
            }
        }
        
        // 설정 섹션 토글
        function toggleSettingsSection() {
            const section = document.getElementById('settingsSection');
            section.classList.toggle('hidden');
            hideOtherSections('settingsSection');
        }

        // 다른 섹션 숨기기
        function hideOtherSections(except) {
            const sections = ['saveSection', 'loadSection', 'addForm', 'settingsSection'];
            sections.forEach(sectionId => {
                if (sectionId !== except) {
                    document.getElementById(sectionId).classList.add('hidden');
                }
            });
        }

        // 파일로 데이터 저장 (개선된 버전)
        async function saveDataToFile() {
            try {
                const customFilename = document.getElementById('saveFilename').value.trim();
                const savePath = document.getElementById('savePath').value.trim();
                
                const requestData = {
                    data: stocks,
                    filename: customFilename,
                    save_path: savePath
                };

                const response = await fetch('/api/save', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(requestData)
                });

                const result = await response.json();
                
                if (result.success) {
                    showStatus(`✅ 데이터가 성공적으로 저장되었습니다!\n파일: ${result.filename}\n경로: ${result.path}`);
                    toggleSaveSection();
                    // 입력 필드 초기화
                    document.getElementById('saveFilename').value = '';
                    document.getElementById('savePath').value = '';
                } else {
                    showStatus(`⌛ 저장 실패: ${result.error}`, true);
                }
            } catch (error) {
                showStatus(`⌛ 저장 중 오류 발생: ${error.message}`, true);
            }
        }

        // 커스텀 경로에서 파일 불러오기
        async function loadFromCustomPath() {
            const filePath = document.getElementById('customFilePath').value.trim();
            
            if (!filePath) {
                showStatus('파일 경로를 입력해주세요.', true);
                return;
            }

            try {
                const response = await fetch('/api/load_file', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ file_path: filePath })
                });

                const result = await response.json();
                
                if (result.success) {
                    stocks = result.data;
                    saveToLocalStorage();
                    renderTable();
                    showStatus(`✅ 데이터가 성공적으로 불러와졌습니다!\n파일: ${result.filename}\n경로: ${result.path}`);
                    toggleLoadSection();
                    document.getElementById('customFilePath').value = '';
                } else {
                    showStatus(`⌛ 불러오기 실패: ${result.error}`, true);
                }
            } catch (error) {
                showStatus(`⌛ 불러오기 중 오류 발생: ${error.message}`, true);
            }
        }

        // 파일 목록 새로고침
        async function refreshFileList() {
            try {
                const response = await fetch('/api/files');
                const result = await response.json();
                
                if (result.success) {
                    displayFileList(result.files);
                } else {
                    showStatus(`⌛ 파일 목록 로드 실패: ${result.error}`, true);
                }
            } catch (error) {
                showStatus(`⌛ 파일 목록 로드 중 오류: ${error.message}`, true);
            }
        }

        // 파일 목록 표시
        function displayFileList(files) {
            const fileList = document.getElementById('fileList');
            
            if (files.length === 0) {
                fileList.innerHTML = '<div style="padding: 20px; text-align: center; color: #6c757d;">저장된 파일이 없습니다.</div>';
                return;
            }

            fileList.innerHTML = files.map(file => `
                <div class="file-item" onclick="selectFile('${file.filename}')">
                    <div class="file-info">
                        <div class="file-name">${file.filename}</div>
                        <div class="file-details">
                            크기: ${(file.size / 1024).toFixed(1)}KB | 
                            수정일: ${file.modified}
                        </div>
                        <div class="path-display">${file.path}</div>
                    </div>
                </div>
            `).join('');
        }

        // 파일 선택
        function selectFile(filename) {
            selectedFileName = filename;
            
            // 선택 상태 업데이트
            document.querySelectorAll('.file-item').forEach(item => {
                item.classList.remove('selected');
            });
            event.currentTarget.classList.add('selected');
            
            // 불러오기 버튼 활성화
            document.getElementById('loadBtn').disabled = false;
        }

        // 선택한 파일 불러오기
        async function loadSelectedFile() {
            if (!selectedFileName) {
                showStatus('파일을 선택해주세요.', true);
                return;
            }

            try {
                const response = await fetch('/api/load', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ filename: selectedFileName })
                });

                const result = await response.json();
                
                if (result.success) {
                    stocks = result.data;
                    saveToLocalStorage();
                    renderTable();
                    showStatus(`✅ 데이터가 성공적으로 불러와졌습니다! 파일: ${result.filename}`);
                    toggleLoadSection();
                } else {
                    showStatus(`⌛ 불러오기 실패: ${result.error}`, true);
                }
            } catch (error) {
                showStatus(`⌛ 불러오기 중 오류 발생: ${error.message}`, true);
            }
        }
        
        // 전체 현재가 업데이트
        async function updateAllPrices() {
            if (stocks.length === 0) {
                showStatus('업데이트할 주식이 없습니다.', true);
                return;
            }

            showStatus('🔄 현재가를 업데이트 중입니다...', false);
            const stockCodes = stocks.map(stock => stock.stockCode);

            try {
                const response = await fetch('/api/update_prices', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ stock_codes: stockCodes, exchange_rate: exchangeRate })
                });

                const result = await response.json();

                if (result.success) {
                    const updatedPrices = result.updated_prices;
                    let updatedCount = 0;
                    
                    stocks = stocks.map(stock => {
                        const newPrice = updatedPrices[stock.stockCode];
                        if (newPrice !== null && newPrice !== undefined) {
                            updatedCount++;
                            let newHighPoint = stock.highPoint;
                            if (newPrice > stock.purchasePrice && newPrice > stock.highPoint) {
                                newHighPoint = newPrice;
                            }
                            return {
                                ...stock,
                                currentPrice: newPrice,
                                highPoint: newHighPoint,
                                lastUpdated: new Date().toLocaleString()
                            };
                        }
                        return stock;
                    });
                    
                    saveToLocalStorage();
                    renderTable();
                    showStatus(`✅ ${updatedCount}개 주식의 현재가가 업데이트되었습니다.`);
                } else {
                    showStatus(`⌛ 현재가 업데이트 실패: ${result.error}`, true);
                }
            } catch (error) {
                showStatus(`⌛ 현재가 업데이트 중 오류 발생: ${error.message}`, true);
            }
        }
        
        // 계산 함수
        function calculateMetrics(stock) {
            const sellPrice = Math.round(stock.highPoint * (1 - sellPercentage / 100));
            const buyMorePrice = Math.round(stock.highPoint * (1 - buyMorePercentage / 100));
            
            const profitLoss = stock.currentPrice >= stock.purchasePrice ? '이익' : '손해';
            
            let opinion;
            if (stock.currentPrice < sellPrice) {
                opinion = '매도';
            } else if ((stock.currentPrice < buyMorePrice) && (stock.currentPrice >= sellPrice)) {
                opinion = '매수';
            } else {
                opinion = '유지';
            }

            return { sellPrice, buyMorePrice, profitLoss, opinion};
        }

        // 폼 토글
        function toggleAddForm() {
            const form = document.getElementById('addForm');
            form.classList.toggle('hidden');
            hideOtherSections('addForm');
            
            if (!form.classList.contains('hidden')) {
                document.getElementById('stockName').focus();
            } else {
                document.getElementById('stockName').value = '';
                document.getElementById('stockCode').value = '';
                document.getElementById('purchasePrice').value = '';
            }
        }

        // 주식 추가
        function addStock() {
            const name = document.getElementById('stockName').value.trim();
            const code = document.getElementById('stockCode').value.trim();
            const purchasePrice = parseInt(document.getElementById('purchasePrice').value);

            if (!name || !code || !purchasePrice || purchasePrice <= 0) {
                alert('주식 이름, 종목 코드, 매입가를 올바르게 입력해주세요.');
                return;
            }

            const stock = {
                id: Date.now(),
                name: name,
                stockCode: code,
                purchasePrice,
                currentPrice: purchasePrice,
                highPoint: purchasePrice,
                lastUpdated: new Date().toLocaleString()
            };

            stocks.push(stock);
            saveToLocalStorage();
            renderTable();
            toggleAddForm();
            showStatus(`✅ ${name} 주식이 추가되었습니다.`);
        }
        
        // 전체 주식 삭제
        function deleteAllStocks() {
            if (stocks.length === 0) {
                showStatus('삭제할 주식이 없습니다.', true);
                return;
            }
            if (confirm('모든 주식 항목을 정말로 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) {
                stocks = [];
                saveToLocalStorage();
                renderTable();
                showStatus('✅ 모든 주식 항목이 삭제되었습니다.');
            }
        }

        // 현재가 업데이트 시작
        function startEdit(id) {
            editingId = id;
            renderTable();
            const input = document.querySelector(`#update-${id}`);
            if (input) {
                input.focus();
                input.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') {
                        updateCurrentPrice(id);
                    }
                });
            }
        }

        // 현재가 업데이트 (수동)
        function updateCurrentPrice(id) {
            const input = document.querySelector(`#update-${id}`);
            const newPrice = parseInt(input.value);
            
            if (!newPrice || newPrice <= 0) {
                alert('올바른 가격을 입력해주세요.');
                return;
            }

            updateStockPrice(id, newPrice);
        }

        // 주식 가격 업데이트 공통 함수
        function updateStockPrice(id, newPrice) {
            stocks = stocks.map(stock => {
                if (stock.id === id) {
                    let newHighPoint = stock.highPoint;
                    if (newPrice > stock.purchasePrice && newPrice > stock.highPoint) {
                        newHighPoint = newPrice;
                    }

                    return {
                        ...stock,
                        currentPrice: newPrice,
                        highPoint: newHighPoint,
                        lastUpdated: new Date().toLocaleString()
                    };
                }
                return stock;
            });

            editingId = null;
            saveToLocalStorage();
            renderTable();
        }

        // 수정 취소
        function cancelEdit() {
            editingId = null;
            renderTable();
        }

        // 주식 삭제
        function deleteStock(id) {
            const stock = stocks.find(s => s.id === id);
            if (confirm(`정말로 "${stock.name}" 주식을 삭제하시겠습니까?`)) {
                stocks = stocks.filter(stock => stock.id !== id);
                saveToLocalStorage();
                renderTable();
                showStatus(`✅ "${stock.name}" 주식이 삭제되었습니다.`);
            }
        }
        
        // 이름 업데이트
        function updateStockName(id, cell) {
            const newName = cell.innerText.trim();
            const stock = stocks.find(s => s.id === id);
            if (!newName) {
                alert('주식 이름은 비워둘 수 없습니다.');
                cell.innerText = stock.name;
                return;
            }
            stock.name = newName;
            saveToLocalStorage();
            renderTable();
            showStatus(`✅ "${newName}"(으)로 주식 이름이 업데이트되었습니다.`);
        }
        
        // 종목 코드 업데이트
        function updateStockCode(id, cell) {
            const newCode = cell.innerText.trim();
            const stock = stocks.find(s => s.id === id);
            if (!newCode) {
                alert('종목 코드는 비워둘 수 없습니다.');
                cell.innerText = stock.stockCode;
                return;
            }
            stock.stockCode = newCode;
            saveToLocalStorage();
            showStatus(`✅ "${stock.name}"의 종목 코드가 ${newCode}(으)로 업데이트되었습니다.`);
        }

        // 매입가 업데이트
        function updatePurchasePrice(id, cell) {
            const newPrice = parseInt(cell.innerText.replace(/[^0-9]/g, ''));
            const stock = stocks.find(s => s.id === id);
            if (isNaN(newPrice) || newPrice <= 0) {
                alert('올바른 매입가를 입력해주세요.');
                cell.innerText = stock.purchasePrice.toLocaleString();
                return;
            }
            stock.purchasePrice = newPrice;
            stock.highPoint = Math.max(stock.highPoint, newPrice);
            saveToLocalStorage();
            renderTable();
            showStatus(`✅ "${stock.name}"의 매입가가 ${newPrice.toLocaleString()}원으로 업데이트되었습니다.`);
        }


        // 테이블 렌더링
        function renderTable() {
            const tbody = document.getElementById('stockTableBody');
            const emptyState = document.getElementById('emptyState');

            if (stocks.length === 0) {
                tbody.innerHTML = '';
                emptyState.style.display = 'block';
                return;
            }

            emptyState.style.display = 'none';
            
            tbody.innerHTML = stocks.map(stock => {
                const { sellPrice, buyMorePrice, profitLoss, opinion } = calculateMetrics(stock);
                
                const profitAmount = stock.currentPrice - stock.purchasePrice;
                const profitRate = ((stock.currentPrice - stock.purchasePrice) / stock.purchasePrice * 100).toFixed(2);
                
                return `
                    <tr>
                        <td contenteditable="true" onblur="updateStockName(${stock.id}, this)"><strong>${stock.name}</strong></td>
                        <td contenteditable="true" onblur="updateStockCode(${stock.id}, this)">${stock.stockCode}</td>
                        <td class="text-right" contenteditable="true" onblur="updatePurchasePrice(${stock.id}, this)">
                            ${stock.purchasePrice.toLocaleString()}원
                        </td>
                        <td class="text-right">
                            ${editingId === stock.id ? `
                                <div class="update-form">
                                    <input type="number" id="update-${stock.id}" class="update-input" 
                                           placeholder="${stock.currentPrice}" />
                                    <button class="btn btn-primary" onclick="updateCurrentPrice(${stock.id})">확인</button>
                                    <button class="btn btn-secondary" onclick="cancelEdit()">취소</button>
                                </div>
                            ` : `
                                <div class="price-info">
                                    <div class="${stock.currentPrice >= stock.purchasePrice ? 'text-green' : 'text-red'}">
                                        ${stock.currentPrice.toLocaleString()}원
                                        <span class="update-icon" onclick="startEdit(${stock.id})" title="수동 입력">✏️</span>
                                    </div>
                                    <div class="small-text ${profitAmount >= 0 ? 'text-green' : 'text-red'}">
                                        (${profitAmount >= 0 ? '+' : ''}${profitAmount.toLocaleString()}원, ${profitRate}%)
                                    </div>
                                </div>
                            `}
                        </td>
                        <td class="text-right">
                            <div class="text-purple">${stock.highPoint.toLocaleString()}원</div>
                            ${stock.highPoint > stock.purchasePrice ? `
                                <div class="small-text text-purple">
                                    (+${((stock.highPoint - stock.purchasePrice) / stock.purchasePrice * 100).toFixed(1)}%)
                                </div>
                            ` : ''}
                        </td>
                        <td class="text-right">
                            <div class="text-red">${sellPrice.toLocaleString()}원</div>
                            <div class="small-text text-red">(고점 -${sellPercentage}%)</div>
                        </td>
                        <td class="text-right">
                            <div class="text-blue">${buyMorePrice.toLocaleString()}원</div>
                            <div class="small-text text-blue">(고점 -${buyMorePercentage}%)</div>
                        </td>
                        <td class="text-center ${profitLoss === '이익' ? 'text-green' : 'text-red'}">
                            <div>${profitLoss}</div>
                            <div class="small-text">${Math.abs(profitAmount).toLocaleString()}원</div>
                        </td>
                        <td class="text-center ${
                            opinion === '매수' ? 'text-blue' : 
                            opinion === '매도' ? 'text-red' : 'text-gray'
                        }">
                            <div>${opinion}</div>
                            <div class="small-text">
                                ${opinion === '매수' ? '추가 매수 구간' : 
                                  opinion === '매도' ? '매도 구간' : '관망 구간'}
                            </div>
                        </td>
                        <td class="text-center">
                            <div class="management-column">
                                <button class="btn btn-danger" onclick="deleteStock(${stock.id})">삭제</button>
                                ${stock.lastUpdated ? `<div class="small-text">${stock.lastUpdated}</div>` : ''}
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');
        }
    </script>
</body>
</html>'''
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("✅ index.html 파일이 생성되었습니다.")

def run_server():
    """웹서버 실행"""
    PORT = 8000
    
    try:
        # HTML 파일 생성
        create_html_file()
        
        # 데이터 폴더 생성
        data_dir = Path("stock_data")
        data_dir.mkdir(exist_ok=True)
        print(f"✅ 데이터 폴더가 준비되었습니다: {data_dir.absolute()}")
        
        # 웹서버 시작
        with socketserver.TCPServer(("", PORT), StockDataHandler) as httpd:
            print(f"🚀 서버가 시작되었습니다!")
            print(f"📱 브라우저에서 http://localhost:{PORT} 접속하세요")
            print(f"🔗 또는 http://127.0.0.1:{PORT} 접속하세요")
            print(f"💾 데이터 파일 저장 위치: {data_dir.absolute()}")
            print(f"ℹ️  서버를 종료하려면 Ctrl+C를 누르세요")
            print("-" * 60)
            
            # 자동으로 브라우저 열기
            try:
                webbrowser.open(f'http://localhost:{PORT}')
                print("🌐 기본 브라우저를 자동으로 열었습니다.")
            except:
                print("⚠️  브라우저를 자동으로 열 수 없습니다. 수동으로 접속해주세요.")
            
            # 서버 실행
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n")
        print("🛑 서버가 종료되었습니다.")
        print("📄 생성된 파일들은 그대로 유지됩니다.")
        print(f"📂 데이터 파일 위치: {Path('stock_data').absolute()}")
    except OSError as e:
        if e.errno == 48 or "Address already in use" in str(e):
            print(f"⌛ 포트 {PORT}가 이미 사용 중입니다.")
            print(f"💡 다른 포트를 사용해보세요: python server.py --port 8001")
        else:
            print(f"⌛ 서버 시작 중 오류 발생: {e}")
    except Exception as e:
        print(f"⌛ 예상치 못한 오류 발생: {e}")

if __name__ == "__main__":
    # yfinance 라이브러리 설치 안내
    try:
        import yfinance as yf
    except ImportError:
        print("=" * 60)
        print("⚠️  yfinance 라이브러리가 설치되어 있지 않습니다.")
        print("⚠️  pip install yfinance 명령어로 설치해주세요.")
        print("=" * 60)
        sys.exit(1)

    # 포트 옵션 처리
    if len(sys.argv) > 2 and sys.argv[1] == "--port":
        try:
            PORT = int(sys.argv[2])
        except ValueError:
            print("⌛ 올바른 포트 번호를 입력하세요.")
            sys.exit(1)
    
    print("=" * 60)
    print("📈 주식 매매 관리 시스템 v2.0 (개선된 파일 관리)")
    print("=" * 60)
    
    run_server()
        