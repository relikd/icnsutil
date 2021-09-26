function dropfile(ev, target, fn) {
    ev.preventDefault();
    let reader = new FileReader();
    reader.readAsArrayBuffer(event.dataTransfer.files[0]);
    reader.onload = function() {
        tgt = document.getElementById(target);
        tgt.value = [...new Uint8Array(reader.result)]
            .map(x => x.toString(16).padStart(2, '0'))
            .join('');
        tgt.dispatchEvent(new KeyboardEvent('keyup', {'key':'a'}));
    };
}


// General

function determine_file_ext(str) {
    let s8 = str.slice(0,8);
    if (s8 == '\x89PNG\x0d\x0a\x1a\x0a') return 'png';
    if (s8 == '\x00\x00\x00\x0CjP  ' || s8 == '\xFF\x4F\xFF\x51\x00\x2F\x00\x00') return 'jp2';
    if (str.slice(0,6) == 'bplist') return 'plist';
    let s4 = str.slice(0,4);
    if (s4 == 'ARGB') return 'argb';
    if (s4 == 'icns') return 'icns';
    if (str.slice(0,3) == '\xFF\xD8\xFF') return 'jpg';
    return null;
}

function icns_type(head) {
    if (['is32', 'il32', 'ih32', 'it32', 'icp4', 'icp5'].indexOf(head) > -1) return 'rgb';
    if (['s8mk', 'l8mk', 'h8mk', 't8mk'].indexOf(head) > -1) return 'mask';
    if (['ICN#', 'icm#', 'ics#', 'ich#'].indexOf(head) > -1) return 'iconmask';
    if (['icm8', 'ics8', 'icl8', 'ich8'].indexOf(head) > -1) return 'icon8b';
    if (['icm4', 'ics4', 'icl4', 'ich4'].indexOf(head) > -1) return 'icon4b';
    if (['sbtp', 'slct', '\xFD\xD9\x2F\xA8'].indexOf(head) > -1) return 'icns';
    if (head == 'ICON') return 'icon1b';
    if (head == 'TOC ') return 'toc';
    if (head == 'info') return 'plist';
    return 'bin';
}

function is_it32(ext, itype, first4b) {
    if (ext == 'rgb') return itype == 'it32';
    if (ext == null) return first4b == [0,0,0,0] || first4b == '00000000';
    return false;
}

function* parse_file(hex_str) {
    function get_length(hex, i) { return Number('0x'+hex.substring(i, i + 8)); }
    function get_str(hex, i, len=8) {
        var str = '';
        for (var u = i; u < i + len; u += 2)
            str += String.fromCharCode(parseInt(hex.substr(u, 2), 16));
        return str;
    }
    function get_media_ext(itype, idx, len) {
        let ext = determine_file_ext(get_str(hex_str, idx, 16));
        if (ext || !itype)
            return [ext, idx, idx + len];
        return [icns_type(itype), idx, idx + len];
    }
    var txt = '';
    var i = 0;
    let ext = get_media_ext(null, 0, hex_str.length);
    if (ext[0] == 'icns') {
        var num = get_length(hex_str, i + 8);
        yield ['icns', i, num, null];
        i += 8 * 2;
        while (i < hex_str.length) {
            let head = get_str(hex_str, i);
            num = get_length(hex_str, i + 8);
            yield [head, i, num, get_media_ext(head, i + 16, num * 2 - 16)];
            i += num * 2;
        }
    } else if (ext[0] == 'argb' || ext[0] == null) {
        yield [null, 0, hex_str.length, ext];
    }
}


// Image viewer

function num_arr_from_hex(hex) {
    var ret = [];
    for (var i = 0; i < hex.length; i += 2)
        ret.push(parseInt(hex.substr(i, 2), 16));
    return ret;
}

function msb_stream(source) {
    var data = [];
    for (var ii = 0; ii < source.length; ii++) {
        let chr = source[ii];
        for (var uu = 7; uu >= 0; uu--) {
            data.push((chr & (1 << uu)) ? 255 : 0);
        }
    }
    return data;
}

function expand_rgb(num_arr) {
    var i = 0;
    var ret = [];
    while (i < num_arr.length) {
        x = num_arr[i];
        i++;
        if (x < 128) {
            for (var u = i; u < i + x + 1; u++) { ret.push(num_arr[u]); }
            i += x + 1;
        } else {
            for (var u = x - 128 + 3; u > 0; u--) { ret.push(num_arr[i]); }
            i++;
        }
    }
    return ret;
}

function make_image(data, channels) {
    let scale = 2;
    let per_channel = data.length / channels;
    let orig_width = Math.sqrt(per_channel);
    let width = orig_width * scale;
    let height = width;

    var canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;

    var ctx = canvas.getContext('2d');
    let map;
    switch (channels) {
      case 1: map = [0, 0, 0, -1]; break;
      case 2: map = [0, 0, 0, 1]; break;
      case 3: map = [0, 1, 2, -1]; break;
      case 4: map = [1, 2, 3, 0]; break;
    }

    for (var i = 0; i < per_channel; i++) {
        let r = data[map[0] * per_channel + i];
        let g = data[map[1] * per_channel + i];
        let b = data[map[2] * per_channel + i];
        let a = (map[3] == -1) ? 255 : data[map[3] * per_channel + i];
        var imagedata = ctx.createImageData(scale, scale);
        for (var idx = scale * scale * 4 - 4; idx >= 0; idx -= 4) {
            imagedata.data[idx] = r;
            imagedata.data[idx + 1] = g;
            imagedata.data[idx + 2] = b;
            imagedata.data[idx + 3] = a;
        }
        let y = Math.floor(i / orig_width);
        let x = i - y * orig_width;
        ctx.putImageData(imagedata, x * scale, y * scale);
    }
    return [canvas, orig_width];
}


// Entry point

function inspect_into(sender, dest) {
    function fn(cls, hex, idx, len, tooltip) {
        var tmp = '';
        for (var u = idx; u < idx + len * 2; u += 2)
            tmp += ' ' + hex[u] + hex[u+1];

        let ttp = tooltip ? ' title="' + tooltip + '"' : '';
        return `<span class="${cls}"${ttp}>${tmp.substring(1)}</span> `;
    }

    let output = document.getElementById(dest);
    output.innerHTML = 'loading ...';
    let src = sender.value.replace(/\s/g, '');
    var txt = '';
    for (let [head, i, len, ext] of parse_file(src)) {
        txt += '<div>';
        if (head) {
            txt += '<h3 id="' + head + '">' + head + '</h3>';
            txt += fn('head', src, i, 4, head);
            txt += fn('len', src, i + 8, 4, 'len:&nbsp;' + len);
        } else {
            txt += '<h3>raw data</h3>';
        }
        if (!ext) { txt += '</div>'; continue; }  // top icns-header

        let abbreviate;
        if (['argb', 'rgb', null].indexOf(ext[0]) > -1) abbreviate = null;
        else if (ext[0] == 'png') abbreviate = 'PNG data';
        else if (ext[0] == 'plist') abbreviate = 'info.plist';
        else if (ext[0] == 'icns') abbreviate = 'icns file';
        else abbreviate = 'raw data';
        if (abbreviate) {
            txt += `<span class="data">... ${abbreviate}, ${len - 8} bytes ...</span>`;
            txt += '</div>';
            continue;
        }

        // parse unpacking
        let is_argb = ext[0] == 'argb';
        var u = ext[1];
        if (is_argb || is_it32(ext[0], head, src.substring(u,u+8))) {
            let title = (ext[0] == 'argb') ? 'ARGB' : 'it32-header';
            txt += fn('head', src, u, 4, title);
            u += 8;
        }
        var total = 0;
        while (u < ext[2]) {
            x = Number('0x'+src[u]+src[u+1]);
            if (x < 128) {
                txt += fn('ctrl', src, u, 1, 'Copy ' + (x + 1) + ' bytes');
                txt += fn('data', src, u + 2, x + 1);
                total += x + 1;
                u += x * 2 + 4;
            } else {
                txt += fn('ctrl', src, u, 1, 'Repeat ' + (x - 128 + 3) + ' times');
                txt += fn('data', src, u + 2, 1);
                total += x - 128 + 3;
                u += 4;
            }
        }
        let w = Math.sqrt(total / (is_argb ? 4 : 3));
        txt += '<p>Image size: ' + w + 'x' + w + '</p>';
        txt += '</div>';
    }
    output.innerHTML = txt;
}

function put_images_into(sender, dest) {
    let src = sender.value.replace(/\s/g, '');
    let output = document.getElementById(dest);
    output.innerHTML = '';
    for (let [head, , , ext] of parse_file(src)) {
        if (!ext) continue;
        if (['argb', 'rgb', 'mask', 'iconmask', 'icon1b', null].indexOf(ext[0]) == -1)
            continue;

        let num_arr = num_arr_from_hex(src.substring(ext[1], ext[2]));
        let ch;
        let data;
        if (ext[0] == 'argb') {
            ch = 4; data = expand_rgb(num_arr.slice(4));
        } else if (ext[0] == 'mask') {
            ch = 1; data = num_arr;
        } else if (ext[0] == 'icon1b') {
            ch = 1; data = msb_stream(num_arr);
        } else if (ext[0] == 'iconmask') {
            ch = 2; data = msb_stream(num_arr);
        } else {
            let it32 = is_it32(ext[0], head, num_arr.slice(0,4));
            ch = 3; data = expand_rgb(it32 ? num_arr.slice(4) : num_arr);
        }
        let [img, w] = make_image(data, ch);
        let container = document.createElement('div');
        container.innerHTML = `<h3>${head || ''}</h3><p>${w}x${w}</p>`
        container.appendChild(img);
        output.appendChild(container);
    }
}
