const REVERSAL=__REVERSAL_DATA__;
$('reversalAvailability').textContent=`${REVERSAL.manifest.input_contracts}계약 → ${REVERSAL.manifest.candidate_events}개 사건 후보 / 필요 가격 ${REVERSAL.manifest.required_anchor_cells}개 중 ${REVERSAL.manifest.observed_anchor_cells}개 확보`;
function updateReversal(){
  const prices=['revPre','revClose','revOpen','revOne','revThirty'].map(id=>$(id).value.trim()===''?NaN:Number($(id).value));
  const valid=prices.every(p=>Number.isFinite(p)&&p>0);
  const labels=['마감 −30분','만기일 종가','다음 시가','+1분','+30분'];
  const pre=valid?prices[1]/prices[0]-1:NaN;
  const values=valid&&pre!==0?prices.slice(2).map(p=>-Math.sign(pre)*(p/prices[1]-1)*10000):[null,null,null];
  $('reversalText').textContent=!valid?'모든 가정 가격에 양의 유한한 값을 입력하세요.':pre===0?'REV 결측: 만기일 마지막 30분 가격 변화가 0입니다.':`가정 REV1 ${values[0].toFixed(2)}bp · REV2 ${values[1].toFixed(2)}bp · REV3 ${values[2].toFixed(2)}bp`;
  draw('reversalPrices',[{x:labels,y:valid?prices:prices.map(()=>null),type:'scatter',mode:'lines+markers',name:'직접 입력한 가정 가격',line:{color:'#d99b25'}}],{yaxis:{title:'가정 가격 (실측 아님)'},margin:{l:60,r:20,t:25,b:80}});
  draw('reversalValues',[{x:['REV1','REV2','REV3'],y:values,type:'bar',name:'가정 가격의 REV',marker:{color:values.map(v=>v===null?'#c7d2df':v>=0?'#148d77':'#d99b25')}}],{yaxis:{title:'REV (bp, 실측 아님)',zeroline:true},margin:{l:60,r:20,t:25,b:80}});
}
for(const id of ['revPre','revClose','revOpen','revOne','revThirty'])$(id).addEventListener('input',updateReversal);
$('downloadReversalEvents').addEventListener('click',()=>saveCSV(REVERSAL.events,'reversal_event_results.csv'));
$('downloadReversalSummary').addEventListener('click',()=>saveCSV(REVERSAL.summary,'reversal_summary.csv'));
$('downloadReversalExamples').addEventListener('click',()=>saveCSV(REVERSAL.examples,'reversal_formula_examples_NOT_MARKET_DATA.csv'));
updateReversal();
