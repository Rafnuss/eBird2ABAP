
[lat,lon] = borders("Kenya");

coastline = load('coast');
lat = coastline.lat;
lon = coastline.long;


%%
res=5/60;

%[X,Y] = meshgrid(34:res:42, -5:res:5);

[X,Y] = meshgrid(-10:res:50, -30:res:30);

X=X(:)'; Y=Y(:)';

in = inpolygon( X, Y,lon, lat);

% figure; hold on; plot(lon,lat); plot(X(in),Y(in),'.k')


X = X(in)+[0 res res 0 0]';
Y = Y(in)+[0 0 res res 0]';

X=round(X,2);
Y=round(Y,2);


% Define the GeoJSON structure
features = cell(size(X,2), 1);
for i = 1:size(X,2)
    
        % Define the current polygon feature
        feature = struct(...
            'type', 'Feature',...
            'geometry', struct(...
                'type', 'Polygon',...
                'coordinates', {{[X(:,i) Y(:,i)]}}...
            ),...
            'properties', struct()...
        );
        
        % Store the current polygon feature in the features cell array
        features{i} = feature;
end

geojson=struct();
geojson.type = 'FeatureCollection';
geojson.features = features;

% Save the GeoJSON file
fid = fopen('africa_pentad.geojson','w');
fprintf(fid,'%s',jsonencode(geojson));
fclose(fid);
