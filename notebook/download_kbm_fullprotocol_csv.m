
%% Download the data for all species in geojson

data_txt = webread("https://api.birdmap.africa/sabap2/v2/coverage/country/kenya", weboptions(Timeout=5*60));
data = jsondecode(data_txt).data;

sp_list = cellfun(@(x) string(x),  {data.species.Ref}');


% sp_kbm = readtable("data/kbm/sp_kbm.xlsx", 'TextType', 'string');
% sp_list = sp_kbm.Ref;

%% Download the files

% Define the directory where to dowlnoad the files
dir_path = 'data/kbm/csv/';

for i_sp=1:numel(sp_list)
    filename =dir_path + sp_list(i_sp)+".csv";
    if sp_list(i_sp) ~="0" %% && ~exist(filename,'file')
        sp_list(i_sp)
        websave(filename,"https://api.birdmap.africa/sabap2/v2/R/2000-07-01/2025-01-01/country/kenya/data/species/"+sp_list(i_sp)+"?format=CSV", weboptions("Timeout",60))
        pause(5)
    end
end


%% Combine files together

% Get list of all csv files in the directory
file_list = dir(fullfile(dir_path, '*.csv')); 
num_files = length(file_list);

% Preallocate cell array
data_cell = cell(num_files, 1);

opts = delimitedTextImportOptions('VariableTypes', {'string', 'datetime', 'datetime', 'duration', 'string', 'double', 'string', 'double', 'double', ...
                 'double', 'double', 'double', 'double', 'double', 'double', 'double', 'double', 'double', ...
                 'double', 'double', 'double', 'double', 'string', 'string', 'string', 'string', 'double'});

opts = detectImportOptions(fullfile(dir_path, file_list(1).name), TextType="string");

% Loop through each file
for k = 1:num_files
    % Read the csv file into a table and store it in the cell array
    data_cell{k} = readtable(fullfile(dir_path, file_list(k).name), opts);
end

% Vertically concatenate all tables in the cell array
merged_data = vertcat(data_cell{cellfun(@height,data_cell)>1});

% Write the merged data to a new csv file
writetable(merged_data,'data/kbm/all.csv');
