from fastapi import FastAPI, UploadFile, File, Form

# === 예시: 정답 채점 결과 엑셀 생성 ===
def build_result_excel(db_df: pd.DataFrame, my_df: pd.DataFrame | None) -> bytes:
out = BytesIO()
with pd.ExcelWriter(out, engine='openpyxl') as xw:
# sheet1: 요약
summary = pd.DataFrame({
'total_problems': [len(db_df)],
'has_my_answers': [my_df is not None]
})
summary.to_excel(xw, index=False, sheet_name='result')


# sheet2: 문제별 상세 (예시 컬럼)
detail = db_df[['problem_id','answer','subject','passage_type','problem_type']].copy() if set(['problem_id','answer','subject','passage_type','problem_type']).issubset(db_df.columns) else db_df.copy()
if my_df is not None and len(my_df.columns) >= 1:
detail['my_answer'] = my_df.iloc[:,0]
detail.to_excel(xw, index=False, sheet_name='detail')


# sheet3: 메타데이터 예시
meta = pd.DataFrame({
'generated_by': ['exam-backend'],
'engine': ['python-docx'],
})
meta.to_excel(xw, index=False, sheet_name='meta')
return out.getvalue()


@app.post('/generate')
async def generate(
student_id: str = Form(...),
title: str = Form(...),
db_file: UploadFile = File(...),
my_answers: UploadFile | None = File(None)
):
try:
db_bytes = await db_file.read()
db_df = pd.read_excel(BytesIO(db_bytes))
my_df = None
if my_answers is not None:
my_bytes = await my_answers.read()
my_df = pd.read_excel(BytesIO(my_bytes))


docx_bytes = build_exam_docx(db_df, title, student_id)
xlsx_bytes = build_result_excel(db_df, my_df)


zip_buf = BytesIO()
with ZipFile(zip_buf, 'w') as zf:
zf.writestr('시험지.docx', docx_bytes)
zf.writestr('결과.xlsx', xlsx_bytes)
zip_buf.seek(0)


return StreamingResponse(zip_buf, media_type='application/zip', headers={
'Content-Disposition': 'attachment; filename=exam_result.zip'
})
except Exception as e:
return PlainTextResponse(str(e), status_code=500)