// ### 통합 JavaScript 시작 ###
let stocks = [];
let tradingLog = [];
let editingId = null;
let managedStockId = null;
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
	
// --- 페이지 로드 및 기본 설정 ---
document.addEventListener('DOMContentLoaded', function() {
	loadFromLocalStorage();
    loadSettings();
    showTab('stocks');
        
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
        
// --- 새로운 기능: 탭, 모달 제어 ---
function showTab(tabName) {
	document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
   	document.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active'));
   	document.getElementById(`tabContent${tabName.charAt(0).toUpperCase() + tabName.slice(1)}`).classList.add('active');
   	document.getElementById(`tabBtn${tabName.charAt(0).toUpperCase() + tabName.slice(1)}`).classList.add('active');
}

function openManagementView(id) {
    managedStockId = id;
    const stock = stocks.find(s => s.id === id);
    if (!stock) return;

    document.getElementById('modalStockName').textContent = stock.name;
    document.getElementById('modalStockCode').textContent = stock.stockCode;
    document.getElementById('modalPurchasePrice').textContent = `${stock.purchasePrice.toLocaleString()}원`;
    document.getElementById('sellPrice').value = stock.currentPrice;

    const sellPriceInput = document.getElementById('sellPrice');
    const profitDisplay = document.getElementById('profitDisplay');
    const calculateProfit = () => {
        const sellPrice = parseInt(sellPriceInput.value) || 0;
        const profit = sellPrice - stock.purchasePrice;
        profitDisplay.value = `${profit.toLocaleString()}원 (${(profit / stock.purchasePrice * 100).toFixed(2)}%)`;
    };
    sellPriceInput.oninput = calculateProfit;
    calculateProfit();

    document.getElementById('sellForm').style.display = 'none';
    document.getElementById('buyForm').style.display = 'none';
    document.getElementById('managementModal').style.display = 'flex';
}

function closeManagementView() {
    document.getElementById('managementModal').style.display = 'none';
    managedStockId = null;
}

function showSellForm() {
    document.getElementById('sellForm').style.display = 'block';
    document.getElementById('buyForm').style.display = 'none';
}

function showBuyForm() {
    document.getElementById('buyForm').style.display = 'block';
    document.getElementById('sellForm').style.display = 'none';
}

// --- 데이터 관리 (저장, 불러오기, 기록) ---
function loadFromLocalStorage() {
    const savedData = localStorage.getItem('stockData');
    if (savedData) {
        const data = JSON.parse(savedData);
        if (Array.isArray(data)) { // 구버전 호환
            stocks = data;
            tradingLog = [];
        } else {
            stocks = data.stocks || [];
            tradingLog = data.tradingLog || [];
        }
    }
    renderTable();
    renderTradingLog();
}

function saveToLocalStorage() {
    const dataToSave = { stocks, tradingLog };
    localStorage.setItem('stockData', JSON.stringify(dataToSave));
}

async function saveDataToFile() {
    try {
        const customFilename = document.getElementById('saveFilename').value.trim();
        const savePath = document.getElementById('savePath').value.trim();
        const requestData = { data: { stocks, tradingLog }, filename: customFilename, save_path: savePath };
        const response = await fetch('/api/save', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(requestData) });
            const result = await response.json();
            if (result.success) {
                showStatus(`✅ 데이터가 성공적으로 저장되었습니다: ${result.path}`);
                toggleSaveSection();
            } else { showStatus(`⌛ 저장 실패: ${result.error}`, true); }
        } catch (error) { showStatus(`⌛ 저장 중 오류 발생: ${error.message}`, true); }
}

function processLoadedData(result) {
    const data = result.data;
    if (Array.isArray(data)) {
        stocks = data;
        tradingLog = [];
    } else {
        stocks = data.stocks || [];
        tradingLog = data.tradingLog || [];
    }
    saveToLocalStorage();
    renderTable();
    renderTradingLog();
    showStatus(`✅ 데이터가 성공적으로 불러와졌습니다!`);
    toggleLoadSection();
}

async function loadFromCustomPath() {
    const filePath = document.getElementById('customFilePath').value.trim();
    if (!filePath) return showStatus('파일 경로를 입력해주세요.', true);
    try {
        const response = await fetch('/api/load_file', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ file_path: filePath }) });
        const result = await response.json();
        if (result.success) processLoadedData(result);
        else showStatus(`⌛ 불러오기 실패: ${result.error}`, true);
        } catch (error) { showStatus(`⌛ 불러오기 중 오류: ${error.message}`, true); }
}
    
async function loadSelectedFile() {
    if (!selectedFileName) return showStatus('파일을 선택해주세요.', true);
    try {
        const response = await fetch('/api/load', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ filename: selectedFileName }) });
        const result = await response.json();
        if (result.success) processLoadedData(result);
        else showStatus(`⌛ 불러오기 실패: ${result.error}`, true);
    } catch (error) { showStatus(`⌛ 불러오기 중 오류: ${error.message}`, true); }
}

// --- 매매 기록 및 주식 관리 로직 ---
function confirmDelete() {
    const stock = stocks.find(s => s.id === managedStockId);
    if (confirm(`정말로 "${stock.name}" 주식을 삭제하시겠습니까?`)) {
        deleteStock(managedStockId);
        closeManagementView();
    }
}

function deleteStock(id) {
    const stock = stocks.find(s => s.id === id);
    stocks = stocks.filter(s => s.id !== id);
    saveToLocalStorage();
    renderTable();
    if (stock) showStatus(`✅ "${stock.name}" 주식이 삭제되었습니다.`);
}

function confirmSell() {
    const stock = stocks.find(s => s.id === managedStockId);
    const sellPrice = parseInt(document.getElementById('sellPrice').value);
    const sellReason = document.getElementById('sellReason').value.trim();
    if (!sellPrice || sellPrice <= 0) return alert('올바른 매도가를 입력해주세요.');
    
    const logEntry = {
        date: new Date().toLocaleString(), name: stock.name, code: stock.stockCode,
        purchasePrice: stock.purchasePrice, sellPrice, 
        profit: sellPrice - stock.purchasePrice, reason: sellReason
    };
    tradingLog.unshift(logEntry);
    //deleteStock(managedStockId);
    
    renderTradingLog();
    saveToLocalStorage();
    closeManagementView();
    showStatus(`✅ "${stock.name}" 매도 기록이 추가되었습니다.`);
}

function confirmBuy() {
    const stock = stocks.find(s => s.id === managedStockId);
    const buyReason = document.getElementById('buyReason').value.trim();
    const logEntry = {
        date: new Date().toLocaleString(), name: stock.name, code: stock.stockCode,
        purchasePrice: stock.purchasePrice, sellPrice: null, profit: null, reason: buyReason
    };
    tradingLog.unshift(logEntry);
    renderTradingLog();
    saveToLocalStorage();
    closeManagementView();
    showStatus(`✅ "${stock.name}" 매수 기록이 추가되었습니다.`);
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
    localStorage.setItem('stockSettings', JSON.stringify({ sellPercentage, buyMorePercentage, exchangeRate }));
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
    setTimeout(() => { statusDiv.style.display = 'none'; }, 5000);
}

    // 저장 섹션 토글
function toggleSaveSection() {
    const section = document.getElementById('saveSection');
    section.classList.toggle('hidden');
    hideOtherSections('saveSection');
    if (!section.classList.contains('hidden')) document.getElementById('saveFilename').focus();
}

    // 불러오기 섹션 토글
function toggleLoadSection() {
    const section = document.getElementById('loadSection');
    section.classList.toggle('hidden');
    hideOtherSections('loadSection');
    if (!section.classList.contains('hidden')) toggleLoadOption();
}

    // 설정 섹션 토글
function toggleSettingsSection() {
    const section = document.getElementById('settingsSection');
    section.classList.toggle('hidden');
    hideOtherSections('settingsSection');
}

    // 다른 섹션 숨기기
function hideOtherSections(except) {
    ['saveSection', 'loadSection', 'addForm', 'settingsSection'].forEach(sectionId => {
        if (sectionId !== except) {
			document.getElementById(sectionId).classList.add('hidden');
		}
    });
}



    // 파일 목록 새로고침
async function refreshFileList() {
    try {
        const response = await fetch('/api/files');
        const result = await response.json();
        if (result.success) displayFileList(result.files);
        else showStatus(`⌛ 파일 목록 로드 실패: ${result.error}`, true);
    } catch (error) { showStatus(`⌛ 파일 목록 로드 중 오류: ${error.message}`, true); }
}

    // 파일 목록 표시
function displayFileList(files) {
    const fileList = document.getElementById('fileList');
    if (files.length === 0) {
        fileList.innerHTML = '<div style="padding: 20px; text-align: center; color: #6c757d;">저장된 파일이 없습니다.</div>';
        return;
    }
    fileList.innerHTML = files.map(file => `
        <div class="file-item" onclick="selectFile(this, '${file.filename}')">
            <div class="file-info">
				<div class="file-name">${file.filename}</div>
				<div class="file-details">크기: ${(file.size / 1024).toFixed(1)}KB | 수정일: ${file.modified}</div>
			</div>
        </div>
	`).join('');
}

    // 파일 선택
function selectFile(element, filename) {
    selectedFileName = filename;
        // 선택 상태 업데이트
    document.querySelectorAll('.file-item').forEach(item => { 
		item.classList.remove('selected')
	});
    element.classList.add('selected');
        // 불러오기 버튼 활성화
    document.getElementById('loadBtn').disabled = false;
}

    // 전체 현재가 업데이트
async function updateAllPrices() {
    if (stocks.length === 0) return showStatus('업데이트할 주식이 없습니다.', true);
    showStatus('🔄 현재가를 업데이트 중입니다...', false);
    try {
        const stockCodes = stocks.map(stock => stock.stockCode);
        const response = await fetch('/api/update_prices', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ stock_codes: stockCodes, exchange_rate: exchangeRate }) });
        const result = await response.json();
        if (result.success) {
            const updatedPrices = result.updated_prices;
            stocks.forEach(stock => {
                const newPrice = updatedPrices[stock.stockCode];
                if (newPrice !== null && newPrice !== undefined) {
                    stock.currentPrice = newPrice;
                    if (newPrice > stock.highPoint) stock.highPoint = newPrice;
                    stock.lastUpdated = new Date().toLocaleString();
                }
            });
            saveToLocalStorage();
            renderTable();
            showStatus(`✅ ${Object.values(updatedPrices).filter(p => p !== null).length}개 주식의 현재가가 업데이트되었습니다.`);
        } else { showStatus(`⌛ 현재가 업데이트 실패: ${result.error}`, true); }
    } catch (error) { showStatus(`⌛ 현재가 업데이트 중 오류 발생: ${error.message}`, true); }
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

function addStock() {
    const name = document.getElementById('stockName').value.trim();
    const code = document.getElementById('stockCode').value.trim();
    const purchasePrice = parseInt(document.getElementById('purchasePrice').value);
    if (!name || !code || !purchasePrice || purchasePrice <= 0) 
		return alert('주식 이름, 종목 코드, 매입가를 올바르게 입력해주세요.');

    stocks.push(
		{ 
			id: Date.now(), 
			name, 
			stockCode: 
			code, 
			purchasePrice, 
			currentPrice: 
			purchasePrice, 
			highPoint: purchasePrice, 
			lastUpdated: new Date().toLocaleString() 
		}
	);
    saveToLocalStorage();
    renderTable();
    toggleAddForm();
    showStatus(`✅ ${name} 주식이 추가되었습니다.`);
}

    // 전체 주식 삭제
function deleteAllStocks() {
    if (stocks.length === 0) return showStatus('삭제할 주식이 없습니다.', true);
    if (confirm('모든 주식 항목을 정말로 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) {
        stocks = [];
        saveToLocalStorage();
        renderTable();
        showStatus('✅ 모든 주식 항목이 삭제되었습니다.');
    }
}

//	function updateCurrentPrice(id, newPrice) { /* 수동 편집 기능 */ }
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

// 프로그램 종료
function showExitModal() {
    document.getElementById('exitModal').style.display = 'flex';
}

function closeExitModal() {
	document.getElementById('exitModal').style.display = 'none';
}

async function exitProgram() {
	try {
    	const response = await fetch('/api/exit', { method: 'POST' });
        const result = await response.json();
	    if (result.success) {
    	    alert('✅ 프로그램이 성공적으로 종료되었습니다.');
            window.close(); // 브라우저 창 닫기 시도
	    } else {
    	    alert(`⚠️ 프로그램 종료 실패: ${result.error}`);
        }
	} catch (error) {
        alert(`⚠️ 서버 연결 오류: ${error.message}\n프로그램을 수동으로 종료해주세요.`);
	}
}

// --- 테이블 렌더링 함수 ---
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

        // --- 새로운 변동 정보 계산 로직 ---
        let priceChangeIcon = '';
        let highPointChangeText = '';
        let highPointChangeClass = 'text-gray';

        // 1. 직전가 대비 상승/하락 아이콘 결정
        if (stock.prevPrice !== undefined && stock.currentPrice !== stock.prevPrice) {
            if (stock.currentPrice > stock.prevPrice) {
                priceChangeIcon = '<span class="price-icon text-green">🔺</span>'; // 상승
            } else if (stock.currentPrice < stock.prevPrice) {
                priceChangeIcon = '<span class="price-icon text-red">🔻</span>'; // 하락
            }
			else {
                priceChangeIcon = '<span class="price-icon text-gray"> - </span>'; // 유지
			}
        }
        
        // 2. 고점 대비 변동 계산
        if (stock.currentPrice > stock.highPoint) {
            // 고점 경신 (로직상 고점 업데이트는 updateAllPrices/updateStockPrice에서 처리됨)
            highPointChangeText = '고점 경신 🎉';
            highPointChangeClass = 'text-green-dark';
        //} else if (stock.highPoint > 0) {
        } else {
        	if (stock.highPoint > 0) {
				const highPointDiffRate = ((stock.currentPrice - stock.highPoint) / stock.highPoint * 100).toFixed(1);
            
            	if (highPointDiffRate < 0) {
                	// 고점 대비 하락률 표시
                	highPointChangeText = `고점 대비 ${highPointDiffRate}%`;
               		highPointChangeClass = 'text-red-dark';
            	} else {
                	// 현재가 == 고점 이거나, 0%에 근접할 경우
                	highPointChangeText = `고점 대비 0.0%`;
                	highPointChangeClass = 'text-gray';
            	}
			}
			else {
            	highPointChangeText = `ERROR`;
            	highPointChangeClass = 'text-red';
			}
        }

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

                <td class="text-center change-info-cell">
                    <div>${priceChangeIcon || '-'}</div>
                    <div class="${highPointChangeClass} high-point-change-text">
                        ${highPointChangeText || '기록 없음'}
                    </div>
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
							<button class="btn btn-primary" onclick="openManagementView(${stock.id})">관리</button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
}

function renderTradingLog() {
    const tbody = document.getElementById('tradingLogBody');
    const emptyState = document.getElementById('tradingLogEmptyState');
    if (tradingLog.length === 0) {
        tbody.innerHTML = '';
        emptyState.style.display = 'block';
        return;
    }
    emptyState.style.display = 'none';
    tbody.innerHTML = tradingLog.map(log => {
        const profitColor = log.profit == null ? '' : (log.profit >= 0 ? 'text-green' : 'text-red');
        return `
            <tr>
                <td>${log.date}</td>
                <td><strong>${log.name}</strong></td>
                <td>${log.code}</td>
                <td class="text-right">${log.purchasePrice.toLocaleString()}원</td>
                <td class="text-right">${log.sellPrice ? log.sellPrice.toLocaleString() + '원' : '-'}</td>
                <td class="text-right ${profitColor}">${log.profit != null ? (log.profit >= 0 ? '+' : '') + log.profit.toLocaleString() + '원' : '-'}</td>
                <td>${log.reason}</td>
            </tr>
        `;
    }).join('');
}
