{{/*
Generate chart name
*/}}
{{- define "vulntracker.name" -}}
{{ .Chart.Name }}
{{- end }}


{{/*
Generate full resource name
*/}}
{{- define "vulntracker.fullname" -}}
{{ .Release.Name }}
{{- end }}