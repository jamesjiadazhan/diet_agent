# Inventory, rather than assume, which FPED entities a combined R bundle holds.
# Large participant-intake files stay in ignored data_sources, never the catalog.
args<-commandArgs(trailingOnly=TRUE)
if(length(args)!=2)stop('Usage: Rscript scripts/inspect_nhanes_reference.R input.Rda output.json')
suppressPackageStartupMessages(library(jsonlite))
e<-new.env(parent=emptyenv());loaded<-load(args[[1]],envir=e)
tables<-list()
visit<-function(x,path){
  if(is.data.frame(x)){
    fields<-names(x)
    kind<-if(any(grepl('^DR[12]T_',fields))) 'participant_daily_intake' else
      if(any(grepl('^DR[12]I',fields))) 'participant_food_intake' else
      if(any(grepl('^(FOODCODE|FOOD_CODE|INGREDIENT_CODE)$',fields,ignore.case=TRUE))) 'food_code_table_requires_unit_and_basis_verification' else 'other'
    tables[[path]]<<-list(rows=nrow(x),columns=fields,kind=kind)
  }else if(is.list(x)){
    for(n in names(x))visit(x[[n]],paste0(path,'$',n))
  }
}
for(n in loaded)visit(e[[n]],n)
result<-list(source=basename(args[[1]]),objects=loaded,tables=tables,
             notice='Participant intakes are validation references; they are not automatically treated as per-100g food composition data.')
write_json(result,args[[2]],pretty=TRUE,auto_unbox=TRUE)
for(n in names(tables))cat(n,':',tables[[n]]$rows,'rows;',tables[[n]]$kind,'\n')
