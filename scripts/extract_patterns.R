# Build-time only. Runtime Python does not require R or readxl.
args<-commandArgs(trailingOnly=TRUE)
if(length(args)!=2)stop("Usage: Rscript scripts/extract_patterns.R workbook.xls output.csv")
suppressPackageStartupMessages(library(readxl))
sheets<-excel_sheets(args[[1]])
if(!any(grepl("2123|2021.*2023",sheets)))stop("Workbook sheets do not identify FPED/FPID 2021-2023; refusing a mismatched release")
for(sheet in sheets){
 d<-read_excel(args[[1]],sheet=sheet,.name_repair="unique")
 if(any(grepl("FOODCODE|FOOD_CODE|INGREDIENT_CODE",names(d),ignore.case=TRUE))){
   write.csv(d,args[[2]],row.names=FALSE,na="");quit(status=0)
 }
}
stop("No supported FPED/FPID component sheet found; inspect workbook headers")
