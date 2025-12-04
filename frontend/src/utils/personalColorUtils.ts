export function normalizePersonalColor(primary: string | undefined | null, sub: string | undefined | null) {
  const p = (primary || '').toString().trim().toLowerCase();
  const s = (sub || '').toString().trim().toLowerCase();

  // normalize primary (웜 / 쿨)
  let primaryNorm: '웜' | '쿨' = '웜';
  if (/쿨|cool|blue|bluebase|블루|실버|차가운/.test(p)) primaryNorm = '쿨';
  else if (/웜|warm|yellow|옐로|gold|따뜻한/.test(p)) primaryNorm = '웜';

  // normalize sub (봄/여름/가을/겨울)
  let subNorm: '봄' | '여름' | '가을' | '겨울' = primaryNorm === '웜' ? '봄' : '여름';

  if (/spring|봄|coral|peach|밝은|화사|bright|clear/.test(s)) subNorm = '봄';
  else if (/summer|여름|pastel|soft|부드러운|파스텔|라벤더/.test(s)) subNorm = '여름';
  else if (/autumn|가을|deep|dark|brown|브라운|카키|차분|깊은/.test(s)) subNorm = '가을';
  else if (/winter|겨울|vivid|clear|진한|강렬|선명|비비드|블랙|화이트/.test(s)) subNorm = '겨울';

  // If sub contains descriptors like 'bright warm' where 'bright' suggests spring
  if (!sub && /bright|clear/.test(p)) {
    subNorm = primaryNorm === '웜' ? '봄' : '겨울';
  }

  const displayName = `${subNorm} ${primaryNorm}톤`;

  return { primary: primaryNorm, sub: subNorm, displayName };
}

export default normalizePersonalColor;
