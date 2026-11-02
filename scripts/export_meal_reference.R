# Independent source-to-score oracle: original USDA JSON + original FPED XLS
# -> R dietaryindex; this deliberately does not read the imported SQLite file.
args<-commandArgs(trailingOnly=TRUE)
if(length(args)!=4)stop('Usage: Rscript scripts/export_meal_reference.R FNDDS.json FPED.xls meals.json output.csv')
suppressPackageStartupMessages({library(dietaryindex);library(readxl);library(jsonlite)})
stopifnot(packageDescription('dietaryindex')$RemoteSha=='0cb60bd67c2942d954d20637500c4a921a935f51')
raw<-fromJSON(args[[1]],simplifyVector=FALSE)$SurveyFoods
raw<-setNames(raw,vapply(raw,function(x)as.character(x$fdcId),character(1)))
p<-read_excel(args[[2]],sheet='FPED_2123')
cols<-grep('\\(',names(p),value=TRUE)
keys<-gsub('[[:space:]]','',sub('\\(.*','',cols))
cases<-fromJSON(args[[3]],simplifyVector=FALSE)
amount<-function(food,number){
  entries<-Filter(function(x)x$nutrient$number==number,food$foodNutrients)
  if(length(entries)!=1 || is.null(entries[[1]]$amount))stop('Missing or duplicate nutrient source')
  entries[[1]]$amount
}
inputs<-lapply(cases,function(case){
  nutrients<-c(kcal=0,sodium=0,saturated_fat=0,mufa=0,pufa=0)
  pattern<-setNames(rep(0,length(keys)),keys)
  for(item in case$foods){
    food<-raw[[as.character(item$fdc_id)]]
    stopifnot(!is.null(food),paste0('fndds-2021-2023:',food$foodCode)==item$food_id)
    factor<-item$portion$value/100
    nutrients<-nutrients+factor*c(kcal=amount(food,'208'),sodium=amount(food,'307'),saturated_fat=amount(food,'606'),mufa=amount(food,'645'),pufa=amount(food,'646'))
    index<-match(as.numeric(food$foodCode),p$FOODCODE)
    stopifnot(!is.na(index))
    pattern<-pattern+factor*as.numeric(unlist(p[index,cols],use.names=FALSE))
  }
  v<-function(...)sum(pattern[c(...)])
  data.frame(id=case$id,age=case$age,kcal=nutrients[['kcal']],
    total_fruit=v('F_TOTAL'),whole_fruit=v('F_CITMLB','F_OTHER'),
    total_vegetable=v('V_TOTAL','V_LEGUMES'),green_and_bean=v('V_DRKGR','V_LEGUMES'),
    total_protein=v('PF_MPS_TOTAL','PF_EGGS','PF_NUTSDS','PF_SOY','PF_LEGUMES'),
    seafood_plant_protein=v('PF_SEAFD_HI','PF_SEAFD_LOW','PF_NUTSDS','PF_SOY','PF_LEGUMES'),
    whole_grain=v('G_WHOLE'),dairy=v('D_TOTAL'),
    fatty_acid=if(nutrients[['saturated_fat']]==0)0 else (nutrients[['mufa']]+nutrients[['pufa']])/nutrients[['saturated_fat']],
    refined_grain=v('G_REFINED'),sodium=nutrients[['sodium']],added_sugar=v('ADD_SUGARS'),saturated_fat=nutrients[['saturated_fat']])
})
d<-do.call(rbind,inputs)
r<-HEI2020_V2(d,RESPONDENTID=d$id,AGE=d$age,TOTALKCAL_HEI2020=d$kcal,
  TOTALFRT_SERV_HEI2020=d$total_fruit,FRT_SERV_HEI2020=d$whole_fruit,
  VEG_SERV_HEI2020=d$total_vegetable,GREENNBEAN_SERV_HEI2020=d$green_and_bean,
  TOTALPRO_SERV_HEI2020=d$total_protein,SEAPLANTPRO_SERV_HEI2020=d$seafood_plant_protein,
  WHOLEGRAIN_SERV_HEI2020=d$whole_grain,DAIRY_SERV_HEI2020=d$dairy,
  FATTYACID_SERV_HEI2020=d$fatty_acid,REFINEDGRAIN_SERV_HEI2020=d$refined_grain,
  SODIUM_SERV_HEI2020=d$sodium,ADDEDSUGAR_SERV_HEI2020=d$added_sugar,SATFAT_SERV_HEI2020=d$saturated_fat)
stopifnot(all(is.finite(r$HEI2020_ALL)))
write.csv(r,args[[4]],row.names=FALSE,na='')
cat('Exported',nrow(r),'independent source-based R meal scores\n')
