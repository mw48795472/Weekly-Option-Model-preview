# Nikkei225 확장 확인 자료

이 폴더에는 TAIFEX API 접근 시도 metadata만 있습니다. 2026-10-13 두 요청 모두 로컬 네트워크 PermissionError로 실패해 원본 응답 파일은 없습니다. 이는 TAIFEX API 서비스 오류나 상품코드 응답이 아닙니다.

공식 [TAIFEX 상품표](https://www.taifex.com.tw/enl/eng2/products)에서 일본 상품은 TOPIX/TJF이며 Nikkei225는 없습니다. 닛케이225 옵션의 정확한 거래소는 [OSE](https://www.jpx.co.jp/english/derivatives/products/domestic/225mini-options/01.html)입니다.

Nikkei/JPX 원본 데이터 및 현물 가격·OI 파일은 확보·공개하지 않았습니다. 권한을 확인한 사용자 입력과 향후 검사 원본은 Git에서 제외되는 data/private/nikkei/에만 보관합니다. 제품 규격 안내의 열람과 실제 시장 데이터 수집 성공을 구분합니다.
