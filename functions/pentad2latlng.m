function [lat0, lng0] = pentad2latlng(p)

p = char(p);

lat0 = str2num(p(:,1:2)) + str2num(p(:,3:4)) / 60;
lng0 = str2num(p(:,6:7)) + str2num(p(:,8:9)) / 60;

id = strcmp(p(:,5),"_") | strcmp(p(:,5),"a");
lat0(id) = -lat0(id);

id = strcmp(p(:,5),"b") | strcmp(p(:,5),"a");
lng0(id) = -lng0(id);


% return center
lng0 = lng0+5/60/2;
lat0 = lat0-5/60/2;

end
