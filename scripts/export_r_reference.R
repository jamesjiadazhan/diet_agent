args <- commandArgs(trailingOnly=TRUE)
output <- if (length(args)) args[[1]] else "tests/fixtures"
dir.create(output, recursive=TRUE, showWarnings=FALSE)
suppressPackageStartupMessages(library(dietaryindex))
pin <- "0cb60bd67c2942d954d20637500c4a921a935f51"
stopifnot(identical(packageDescription("dietaryindex")$RemoteSha, pin))
score <- function(d, fun) {
  fun(d, RESPONDENTID=d$id, AGE=d$age, TOTALKCAL_HEI2020=d$kcal,
      TOTALFRT_SERV_HEI2020=d$total_fruit, FRT_SERV_HEI2020=d$whole_fruit,
      VEG_SERV_HEI2020=d$total_vegetable, GREENNBEAN_SERV_HEI2020=d$green_and_bean,
      TOTALPRO_SERV_HEI2020=d$total_protein, SEAPLANTPRO_SERV_HEI2020=d$seafood_plant_protein,
      WHOLEGRAIN_SERV_HEI2020=d$whole_grain, DAIRY_SERV_HEI2020=d$dairy,
      FATTYACID_SERV_HEI2020=d$fatty_acid, REFINEDGRAIN_SERV_HEI2020=d$refined_grain,
      SODIUM_SERV_HEI2020=d$sodium, ADDEDSUGAR_SERV_HEI2020=d$added_sugar,
      SATFAT_SERV_HEI2020=d$saturated_fat)
}
for (name in c("HEI2020_VALIDATION", "HEI2020_V2_VALIDATION")) {
  e<-new.env();data(list=name,package="dietaryindex",envir=e);d<-e[[name]]
  write.csv(d,file.path(output,paste0(name,".csv")),row.names=FALSE)
  # Each fixture already uses the corresponding R function's input units.
  x<-d
  r<-score(x,if(name=="HEI2020_VALIDATION") HEI2020 else HEI2020_V2)
  write.csv(r,file.path(output,paste0(name,"_r_output.csv")),row.names=FALSE)
}
set.seed(20261101)
n<-1000
d<-data.frame(id=seq_len(n),age=sample(c(1,1.5,1.999,2,18,65),n,replace=TRUE),kcal=runif(n,100,5000))
for (field in c("total_fruit","whole_fruit","total_vegetable","green_and_bean","total_protein","seafood_plant_protein","whole_grain","dairy","refined_grain")) d[[field]]<-runif(n,0,8)
d$fatty_acid<-runif(n,0,5);d$sodium<-runif(n,0,10000);d$added_sugar<-runif(n,0,60);d$saturated_fat<-runif(n,0,100)
write.csv(d,file.path(output,"hei_random_inputs.csv"),row.names=FALSE)
write.csv(score(d,HEI2020_V2),file.path(output,"hei_random_r_output.csv"),row.names=FALSE)
