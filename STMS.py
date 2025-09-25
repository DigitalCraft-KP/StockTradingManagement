# STMS(StockTradingManagementSystem).py

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

# HTML file path
HTML_FILE = "index.html"

class StockDataHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        """Handle POST requests (data save/load)"""
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
        elif self.path == '/api/exit': # Exit Program
            self.exit_program()
        else:
            self.send_error(404)
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/api/files':
            self.list_files()
        elif self.path == '/':
            # Serve the main HTML file
            self.path = HTML_FILE
            super().do_GET()
        else:
            super().do_GET()
    
    def update_prices(self):
        """Update current prices using stock codes"""
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
                    print(f"⌛ Error updating price for {code}: {e}")
                    updated_stocks[code] = None

            response = {"success": True, "updated_prices": updated_stocks}
            self.send_json_response(response)
            
        except Exception as e:
            error_response = {"success": False, "error": str(e)}
            self.send_json_response(error_response, 500)

    def update_exchange_rate(self):
        """Update real-time exchange rate (USD→KRW)"""
        try:
            ticker = yf.Ticker("USDKRW=X")
            exchange_rate = ticker.info.get("regularMarketPrice")

            if exchange_rate:
                response = {"success": True, "exchange_rate": round(exchange_rate, 2)}
            else:
                response = {"success": False, "error": "Could not fetch exchange rate."}

            self.send_json_response(response)

        except Exception as e:
            error_response = {"success": False, "error": str(e)}
            self.send_json_response(error_response, 500)

    def exit_program(self):
        """Exit the program safely"""
        print("\n")
        print("🛑 Received exit request. Shutting down the server...")
        self.send_json_response({"success": True})
        # This will raise a KeyboardInterrupt to stop the server loop.
        # It mimics a manual Ctrl+C press.
        import threading
        threading.Thread(target=self.server.shutdown).start()



    def save_data(self):
        """Save data to a JSON file (supports custom filename)"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            data = request_data.get('data', {}) # 수정: 데이터가 JSON 객체 형태로 들어옴
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
        """Load JSON file from the default stock_data folder"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            filename = request_data.get('filename')
            if not filename:
                raise ValueError("Filename is required.")
            
            file_path = Path("stock_data") / filename
            
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {filename}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            response = {"success": True, "data": data, "filename": filename}
            self.send_json_response(response)
            
        except Exception as e:
            error_response = {"success": False, "error": str(e)}
            self.send_json_response(error_response, 500)
    
    def load_file_from_path(self):
        """Load JSON file from an arbitrary path"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            file_path = request_data.get('file_path')
            if not file_path:
                raise ValueError("File path is required.")
            
            file_path = Path(file_path)
            
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            if not file_path.suffix.lower() == '.json':
                raise ValueError("Only JSON files are supported.")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            response = {"success": True, "data": data, "filename": file_path.name, "path": str(file_path.absolute())}
            self.send_json_response(response)
            
        except Exception as e:
            error_response = {"success": False, "error": str(e)}
            self.send_json_response(error_response, 500)
    
    def list_files(self):
        """Return a list of saved files"""
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
        """Send a JSON response"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
        response_json = json.dumps(data, ensure_ascii=False)
        self.wfile.write(response_json.encode('utf-8'))

def run_server():
    """Run the web server"""
    PORT = 8000
    
    try:     
        # 데이터 폴더 생성
        data_dir = Path("stock_data")
        data_dir.mkdir(exist_ok=True)
        print(f"✅ Data folder is ready: {data_dir.absolute()}")
        
        # 웹서버 시작
        with socketserver.TCPServer(("", PORT), StockDataHandler) as httpd:
            print(f"🚀 Server started!")
            print(f"📱 Access http://localhost:{PORT} in your browser")
            print(f"🔗 Or http://127.0.0.1:{PORT}")
            print(f"💾 Data files are stored in: {data_dir.absolute()}")
            print(f"ℹ️  Press Ctrl+C to stop the server")
            print("-" * 60)
            
            # 자동으로 브라우저 열기
            try:
                webbrowser.open(f'http://localhost:{PORT}')
                print("🌐 Automatically opened the default browser.")
            except:
                print("⚠️  Could not open the browser automatically. Please access manually.")
            
            # 서버 실행
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n")
        print("🛑 Server stopped.")
        print("📄 Generated files are kept.")
        print(f"📂 Data file location: {Path('stock_data').absolute()}")
    except OSError as e:
        if e.errno == 48 or "Address already in use" in str(e):
            print(f"⌛ Port {PORT} is already in use.")
            print(f"💡 Try another port: python server.py --port 8001")
        else:
            print(f"⌛ Error starting server: {e}")
    except Exception as e:
        print(f"⌛ Unexpected error occurred: {e}")

if __name__ == "__main__":
    # yfinance 라이브러리 설치 안내
    try:
        import yfinance as yf
    except ImportError:
        print("=" * 60)
        print("⚠️  The yfinance library is not installed.")
        print("⚠️  Please install it with: pip install yfinance")
        print("=" * 60)
        sys.exit(1)

    # 포트 옵션 처리
    if len(sys.argv) > 2 and sys.argv[1] == "--port":
        try:
            PORT = int(sys.argv[2])
        except ValueError:
            print("⌛ Please enter a valid port number.")
            sys.exit(1)
    
    print("=" * 60)
    print("📈 Stock Trading Management System by KP)")
    print("=" * 60)
    
    run_server()
