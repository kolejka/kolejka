#!/bin/sh
# vim:ts=4:sts=4:sw=4:expandtab

MOUNT="/kolejka_python"
TEMP="${MOUNT}/update"
DEST="${MOUNT}/current"
OLD="${MOUNT}/old"

apk update &&
apk upgrade &&
apk add python3 &&
rm -rf /var/cache/apk &&
mkdir -p /var/cache/apk &&
mkdir -p "${TEMP}" &&
cp -a /bin /etc /lib /sbin /usr /var /tmp "${TEMP}" &&
mkdir "${TEMP}/dev" "${TEMP}/home" "${TEMP}/proc" "${TEMP}/root" "${TEMP}/run" "${TEMP}/srv" &&
touch "${TEMP}/python3" &&
chmod 755 "${TEMP}/python3" &&
cat > "${TEMP}/python3" <<EOF
#!/bin/sh
# This script requires:
# which
# readlink
# dirname
# find
# env
# cut
# TODO: remove which and find.

MYSELF="\$(readlink -f "\$(which "\${0}")")"
OFFICE="\$(dirname "\${MYSELF}")"

EXEC_LDSO="\$(find "\${OFFICE}/lib" -maxdepth 1 -name "ld-*.so.?" -type f)"
EXEC_PYTHON="\${OFFICE}/usr/bin/python3"

ENV_USER="\${USER}"
ENV_HOME="\${HOME}"
ENV_TERM="\${TERM}"
ENV_PWD="\${PWD}"

env |cut -d = -f 1 |while read v; do
    unset "\${v}";
done

if [ -n "\${ENV_USER}" ]; then
    export USER="\${ENV_USER}"
fi
if [ -n "\${ENV_HOME}" ]; then
    export HOME="\${ENV_HOME}"
fi
if [ -n "\${ENV_TERM}" ]; then
    export TERM="\${ENV_TERM}"
fi

export PWD="\${ENV_PWD}"
export IFS=" "

export PATH="\${OFFICE}/usr/bin:\${OFFICE}/bin"
export LD_LIBRARY_PATH="\${OFFICE}/usr/lib:\${OFFICE}/lib"
export PYTHONHOME="\${OFFICE}/usr"

if [ -n "\${EXEC_LDSO}" -a -n "\${EXEC_PYTHON}" ]; then
    exec "\${EXEC_LDSO}" -- "\${EXEC_PYTHON}" "\$@"
fi

exit 1
EOF

if [ -x "${TEMP}"/python3 ]; then
    rm -rf "${OLD}"
    mv "${DEST}" "${OLD}"
    mv "${TEMP}" "${DEST}"
    rm -rf "${OLD}"
    touch "${MOUNT}/python3"
    chmod 755 "${MOUNT}/python3"
    cat > "${MOUNT}/python3" <<EOF
#!/bin/sh
MYSELF="\$(readlink -f "\$(which "\${0}")")"
OFFICE="\$(dirname "\${MYSELF}")"
exec "\${OFFICE}/current/python3" "\$@"
EOF
    exit 0
fi

exit 1
